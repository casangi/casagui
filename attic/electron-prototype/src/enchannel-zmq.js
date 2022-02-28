"use strict";
var __importStar = (this && this.__importStar) || function (mod) {
    if (mod && mod.__esModule) return mod;
    var result = {};
    if (mod != null) for (var k in mod) if (Object.hasOwnProperty.call(mod, k)) result[k] = mod[k];
    result["default"] = mod;
    return result;
};
Object.defineProperty(exports, "__esModule", { value: true });
const moduleJMP = require("./jmp");
const rxjs_1 = require("rxjs");
const operators_1 = require("rxjs/operators");
const uuid_1 = require("uuid");
exports.ZMQType = {
    frontend: {
        iopub: "sub",
        stdin: "dealer",
        shell: "dealer",
        control: "dealer"
    }
};
/**
 * Takes a Jupyter spec connection info object and channel and returns the
 * string for a channel. Abstracts away tcp and ipc connection string
 * formatting
 *
 * @param config  Jupyter connection information
 * @param channel Jupyter channel ("iopub", "shell", "control", "stdin")
 *
 * @returns The connection string
 */
exports.formConnectionString = (config, channel) => {
    const portDelimiter = config.transport === "tcp" ? ":" : "-";
    const port = config[`${channel}_port`];
    if (!port) {
        throw new Error(`Port not found for channel "${channel}"`);
    }
    return `${config.transport}://${config.ip}${portDelimiter}${port}`;
};
/**
 * Creates a socket for the given channel with ZMQ channel type given a config
 *
 * @param channel Jupyter channel ("iopub", "shell", "control", "stdin")
 * @param identity UUID
 * @param config  Jupyter connection information
 *
 * @returns The new Jupyter ZMQ socket
 */
exports.createSocket = (channel, identity, config, jmp = moduleJMP) => {
    const zmqType = exports.ZMQType.frontend[channel];
    const scheme = config.signature_scheme.slice("hmac-".length);
    const socket = new jmp.Socket(zmqType, scheme, config.key);
    socket.identity = identity;
    const url = exports.formConnectionString(config, channel);
    return exports.verifiedConnect(socket, url);
};
/**
 * Ensures the socket is ready after connecting.
 *
 * @param socket A 0MQ socket
 * @param url Creates a connection string to connect the socket to
 *
 * @returns A Promise resolving to the same socket.
 */
exports.verifiedConnect = (socket, url) => new Promise(resolve => {
    socket.on("connect", () => {
        // We are not ready until this happens for all the sockets
        socket.unmonitor();
        resolve(socket);
    });
    socket.monitor();
    socket.connect(url);
});
exports.getUsername = () => process.env.LOGNAME ||
    process.env.USER ||
    process.env.LNAME ||
    process.env.USERNAME ||
    "username"; // This is the fallback that the classic notebook uses
/**
 * Creates a multiplexed set of channels.
 *
 * @param  config                  Jupyter connection information
 * @param  config.ip               IP address of the kernel
 * @param  config.transport        Transport, e.g. TCP
 * @param  config.signature_scheme Hashing scheme, e.g. hmac-sha256
 * @param  config.iopub_port       Port for iopub channel
 * @param  subscription            subscribed topic; defaults to all
 * @param  identity                UUID
 *
 * @returns Subject containing multiplexed channels
 */
exports.createMainChannel = async (config, subscription = "", identity = uuid_1.v4(), header = {
    session: uuid_1.v4(),
    username: exports.getUsername()
}, jmp = moduleJMP) => {
    const sockets = await exports.createSockets(config, subscription, identity, jmp);
    const main = exports.createMainChannelFromSockets(sockets, header, jmp);
    return main;
};
/**
 * Sets up the sockets for each of the jupyter channels.
 *
 * @param config Jupyter connection information
 * @param subscription The topic to filter the subscription to the iopub channel on
 * @param identity UUID
 * @param jmp A reference to the JMP Node module
 *
 * @returns Sockets for each Jupyter channel
 */
exports.createSockets = async (config, subscription = "", identity = uuid_1.v4(), jmp = moduleJMP) => {
    const [shell, control, stdin, iopub] = await Promise.all([
        exports.createSocket("shell", identity, config, jmp),
        exports.createSocket("control", identity, config, jmp),
        exports.createSocket("stdin", identity, config, jmp),
        exports.createSocket("iopub", identity, config, jmp)
    ]);
    // NOTE: ZMQ PUB/SUB subscription (not an Rx subscription)
    iopub.subscribe(subscription);
    return {
        shell,
        control,
        stdin,
        iopub
    };
};
/**
 * Creates a multiplexed set of channels.
 *
 * @param sockets An object containing associations between channel types and 0MQ sockets
 * @param header The session and username to place in kernel message headers
 * @param jmp A reference to the JMP Node module
 *
 * @returns Creates an Observable for each channel connection that allows us
 * to send and receive messages through the Jupyter protocol.
 */
exports.createMainChannelFromSockets = (sockets, header = {
    session: uuid_1.v4(),
    username: exports.getUsername()
}, jmp = moduleJMP) => {
    // The mega subject that encapsulates all the sockets as one multiplexed
    // stream
    const outgoingMessages = rxjs_1.Subscriber.create(message => {
        // There's always a chance that a bad message is sent, we'll ignore it
        // instead of consuming it
        if (!message || !message.channel) {
            console.warn("message sent without a channel", message);
            return;
        }
        const socket = sockets[message.channel];
        if (!socket) {
            // If, for some reason, a message is sent on a channel we don't have
            // a socket for, warn about it but don't bomb the stream
            console.warn("channel not understood for message", message);
            return;
        }
        try {
            const jMessage = new jmp.Message({
                // Fold in the setup header to ease usage of messages on channels
                header: Object.assign(Object.assign({}, message.header), header),
                parent_header: message.parent_header,
                content: message.content,
                metadata: message.metadata,
                buffers: message.buffers
            });
            socket.send(jMessage);
        }
        catch (err) {
            console.error("Error sending message", err, message);
        }
    }, undefined, // not bothering with sending errors on
    () => 
    // When the subject is completed / disposed, close all the event
    // listeners and shutdown the socket
    Object.keys(sockets).forEach(name => {
        const socket = sockets[name];
        socket.removeAllListeners();
        if (socket.close) {
            socket.close();
        }
    }));
    // Messages from kernel on the sockets
    const incomingMessages = rxjs_1.merge(
    // Form an Observable with each socket
    ...Object.keys(sockets).map(name => {
        const socket = sockets[name];
        // fromEvent typings are broken. socket will work as an event target.
        return rxjs_1.fromEvent(
        // Pending a refactor around jmp, this allows us to treat the socket
        // as a normal event emitter
        socket, "message").pipe(operators_1.map((body) => {
            // Route the message for the frontend by setting the channel
            const msg = Object.assign(Object.assign({}, body), { channel: name });
            // Conform to same message format as notebook websockets
            // See https://github.com/n-riesco/jmp/issues/10
            delete msg.idents;
            return msg;
        }), operators_1.publish(), operators_1.refCount());
    })).pipe(operators_1.publish(), operators_1.refCount());
    const subject = rxjs_1.Subject.create(outgoingMessages, incomingMessages);
    return subject;
};
