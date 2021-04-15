import { message, Channels, MessageType } from "@nteract/messaging";
import { EventEmitter } from "events";
const { v4: uuidv4 } = require('uuid');
const awaiting = require("awaiting");
const callback = awaiting.callback;
const { reuseInFlight } = require("async-await-utils/hof");
import { len, deep_copy, debug } from "./utils";

import { ChildProcess } from "child_process";
const { findAll } = require("../src/kernel-specs");
const { launchSpec } = require("../src/spawnteract");
const { JupyterConnectionInfo, createSocket, createMainChannel } = require("../src/enchannel-zmq");
const path = require('path')

const jmp = require("../src/jmp");

export { MessageType as message_type } from "@nteract/messaging";

export enum KernelLocation {
    // Future kernel locations: Remote (cluster), AWS, etc.
    Local = "kernel/location/local"
}

export enum KernelStatus {
    Launched = "kernel/status/launched"
}
const username = process.env.LOGNAME || process.env.USER || process.env.LNAME || process.env.USERNAME;

export async function kerneldesc( name: string, location: KernelLocation, debug=false ): Promise<any> {
    function desc( kv: any ) {
        return { name: kv.name,
                 files: kv.files,
                 kernid: uuidv4( ),
                 header: { session: uuidv4( ), username: username },
                 resource_dir: kv.resource_dir ?? kv.resources_dir,
                 display_name: kv.spec.display_name,
                 language: kv.spec.language,
                 interrupt_mode: kv.spec.interrupt_mode,
                 env: kv.spec.env,
                 metadata: kv.spec.metadata,
                 argv: kv.spec.argv,
                 location
               }
    }
    return findAll( ).then( (kernels: {[key: string]: any}) => {
        var result = undefined
        for (let k in kernels) if ( k === name ) {
            result = desc(kernels[k])
        }
        if ( result ) {
            if ( debug ) {
                result.argv.splice(5, 0, "--debug");
                result.argv.splice(5, 0, "--Session.debug=True")
                result.argv.splice(5, 0, `/tmp/ipy-kern-${process.pid}.txt`)
                result.argv.splice(5, 0, "--logfile")
                console.log(result.argv)
            }
            return result
        }
        throw new Error(`kernel not found: ${name}`)
    } )
}

// accepts a kernel description (info needed to start a kernel)
// returns launch info (basic info about the running kernel)
export async function launch( desc: any, cwd: string = ".") {
    // from https://stackoverflow.com/questions/14780350/convert-relative-path-to-absolute-using-javascript
    const kernel_desc = { language: desc.language,
                          display_name: desc.display_name,
                          argv: desc.argv
                        }
    cwd = path.resolve(cwd)
    return launchSpec( kernel_desc, { cwd, stdio: ["ignore", "pipe", "pipe"],
                                      env: { PLOTLY_RENDERER: "colab" } } ).then(
        async( cfg: { config: any;
                      spawn: ChildProcess;
                      connectionFile: string } ) => {
                          // session is the CASA GUI identifier (independent of where/how kernel is started)
                          return { kernid: desc.kernid, header: desc.header, location: desc.location,
                                   config: cfg.config, spawn: cfg.spawn, file: cfg.connectionFile, initialdir: cwd }
                      } )
}


// accepts launch info (basic info about the running kernel)
// returns a kernel handle (which includes the channels necessary for sending messages to the kernel)
export async function channels( launch_info: { config: any; kernid: any; header: any; location: any;
                                               spawn:any; file: string; initialdir: string } ) {
    // create one channel which can multiplex all of the channels
    return createMainChannel( launch_info.config, "", launch_info.kernid, launch_info.header, jmp ).then(
           (channels: {[key: string]: any}) => {
                   return { kernid: launch_info.kernid,
                            location: launch_info.location,
                            header: launch_info.header,
                            ipc: "zeromq",
                            config: launch_info.config,
                            spawn: launch_info.spawn,
                            file: launch_info.file,
                            initialdir: launch_info.initialdir,
                            channel: channels,
                          }
    } )
}


export const VERSION = "5.3";

/* retry_until_success keeps calling an async function f with
  exponential backoff until f does NOT raise an exception.
  Then retry_until_success returns whatever f returned.
*/

interface RetryUntilSuccess<T> {
    f: () => Promise<T>; // an async function that takes no input.
    start_delay?: number; // milliseconds -- delay before calling second time.
    max_delay?: number; // milliseconds -- delay at most this amount between calls
    max_tries?: number; // maximum number of times to call f
    max_time?: number; // milliseconds -- don't call f again if the call would start after this much time from first call
    factor?: number; // multiply delay by this each time
    log?: Function; // optional verbose logging function
    desc?: string; // useful for making error messages better.
}

export async function retry_until_success<T>(
    opts: RetryUntilSuccess<T>
): Promise<T> {
    if (!opts.start_delay) opts.start_delay = 100;
    if (!opts.max_delay) opts.max_delay = 20000;
    if (!opts.factor) opts.factor = 1.4;

    let next_delay: number = opts.start_delay;
    let tries: number = 0;
    const start_time: number = new Date().valueOf();
    let last_exc: Error | undefined;

    // Return nonempty string if time or tries exceeded.
    function check_done(): string {
        if ( opts.max_time &&
             next_delay + new Date().valueOf() - start_time > opts.max_time
           ) {
            return "maximum time exceeded";
        }
        if (opts.max_tries && tries >= opts.max_tries) {
            return "maximum tries exceeded";
        }
        return "";
    }

    while (true) {
        try {
            return await opts.f();
        } catch (exc) {
            //console.warn('retry_until_success', exc);
            if (opts.log !== undefined) {
                opts.log("failed ", exc);
            }
            // might try again -- update state...
            tries += 1;
            next_delay = Math.min(opts.max_delay, opts.factor * next_delay);
            // check if too long or too many tries
            const err = check_done();
            if (err) {
                // yep -- game over, throw an error
                let e;
                if (last_exc) {
                    e = Error(`${err} -- last error was ${last_exc} -- ${opts.desc}`);
                } else {
                    e = Error(`${err} -- ${opts.desc}`);
                }
                //console.warn(e);
                throw e;
            }
            // record exception so can use it later.
            last_exc = exc;

            // wait before trying again
            await awaiting.delay(next_delay);
        }
    }
}

export class JupyterKernel
extends EventEmitter
{
    private _kernel: any;
    //public channel?: Channels;
    public channel: any;
    public stderr: string = "";
    private _state: string = "off";
    private has_ensured_running: boolean = false;

    constructor( ) {
        super( );
        this._set_state("off");
    }

    async foobar( what: string ): Promise<any> {
        return `OK Got: ${what}`
    }

    private _set_state(state: string): void {
        // state = 'off' --> 'spawning' --> 'starting' --> 'running' --> 'closed'
        this._state = state;
        this.emit("state", this._state);
    }

    public get_state(): string {
        return this._state;
    }

    async close(): Promise<void> {
        if (this._state === "closed") {
            return;
        }
        const spawn = this._kernel != null ? this._kernel.spawn : undefined;
        const pid = spawn?.pid;
        debug("kernels",`closing kernel: ${pid}`)
        this._set_state("closed");
    }

    async spawn(spawn_opts?: any): Promise<any> {
        if (this._state === "closed") {
            // game over!
            throw Error("closed");
        }
        if (["running", "starting"].includes(this._state)) {
            // Already spawned, so no need to do it again.
            return;
        }
        this._set_state("spawning");
        debug("kernels","spawning kernel");

        //const opts: LaunchJupyterOpts = {
        //    detached: true,
        //    env: spawn_opts?.env ?? {},
        //};

        //if (this.name.indexOf("sage") == 0) {
        //    dbg("setting special environment for sage.* kernels");
        //    opts.env = merge(opts.env, SAGE_JUPYTER_ENV);
        //}

        // Make cocalc default to the colab renderer for cocalc-jupyter, since
        // this one happens to work best for us, and they don't have a custom
        // one for us.  See https://plot.ly/python/renderers/ and
        // https://github.com/sagemathinc/cocalc/issues/4259
        //opts.env.PLOTLY_RENDERER = "colab";

        // expose path of jupyter notebook -- https://github.com/sagemathinc/cocalc/issues/5165
        //opts.env.COCALC_JUPYTER_FILENAME = this._path;
        //opts.env.COCALC_JUPYTER_KERNELNAME = this.name;

        //if (this._directory !== "") {
        //    opts.cwd = this._directory;
        //}

        try {
            debug("kernels","launching kernel interface...")
            this._kernel = await kerneldesc('python3',KernelLocation.Local /*,true*/).then(launch)
            await this.finish_spawn( );
        } catch (err) {
            if (this._state === "closed") {
                throw Error("closed");
            }
            this._set_state("off");
            throw err;
        }
        return { identity: this._kernel.kernid,
                 config: this._kernel.config,
                 header: this._kernel.header }
    }
    private async finish_spawn(): Promise<void> {
        debug("kernels","now finishing spawn of kernel...")

        this._kernel.spawn.on("error", (err: any) => {
            const error = `${err}\n${this.stderr}`;
            debug("kernels",error)
            this.emit("error", error);
        });

        // Track stderr from the subprocess itself (the kernel).
        // This is useful for debugging broken kernels, etc., and is especially
        // useful since it exists even if the kernel sends nothing over any
        // zmq channels (e.g., due to being very broken).
        //this.stderr = "";
        this._kernel.spawn.stderr.on("data", (data: any) => {
            const s = data.toString();
            this.stderr += s;
            if (this.stderr.length > 5000) {
                // truncate if gets long for some reason -- only the end will
                // be useful...
                this.stderr = this.stderr.slice(this.stderr.length - 4000);
            }
            debug("kernels","execa:stderr", this.stderr)
        });

        this._kernel.spawn.stdout.on("data", (_data: any) => {
            // NOTE: it is very important to read stdout (and stderr above)
            // even if we **totally ignore** the data. Otherwise, execa saves
            // some amount then just locks up and doesn't allow flushing the
            // output stream.  This is a "nice" feature of execa, since it means
            // no data gets dropped.  See https://github.com/sagemathinc/cocalc/issues/5065
            debug("kernels","execa:stdout", _data.toString( ))
        });

        debug("kernels","launch description:", this._kernel)
        this.channel = await channels(this._kernel)
        debug("kernels","channel description:", this.channel)
        this.channel?.channel.subscribe((mesg: any) => {
            switch (mesg.channel) {
            case "shell":
                debug("kernels","received shell message:",mesg)
                this.emit("shell", mesg);
                break;
            case "stdin":
                this.emit("stdin", mesg);
                debug("kernels","received stdin message:",mesg)
                break;
            case "iopub":
                if (mesg.content != null && mesg.content.execution_state != null) {
                    this.emit("execution_state", mesg.content.execution_state);
                }

                if ( (mesg.content != null ? mesg.content.comm_id : undefined) !== undefined ) {
                    // A comm message, which gets handled directly.
                    //this.process_comm_message_from_kernel(mesg);
                    //this.process_comm_message_from_kernel(mesg);
                    debug("kernels", "comm message", mesg)
                    break;
                }
                //if ( this._actions != null &&
                //     this._actions.capture_output_message(mesg)
                //   ) {
                //    // captured an output message -- do not process further
                //    break;
                //}

                debug("kernels", "iopub message received", mesg)
                this.emit("iopub", mesg);
                break;
            }
        });

        this._kernel.spawn.on("exit", (exit_code: any, signal: any) => {
            debug("kernel",`spawned kernel terminated with exit code ${exit_code} (signal=${signal}); stderr=${this.stderr}`)

            if (signal != null) {
                this.emit("error",`Kernel last terminated by signal ${signal}.${this.stderr}`)
            } else if (exit_code != null) {
                this.emit("error",`Kernel last exited with code ${exit_code}.${this.stderr}`)
            }
            this.close();
        });

        // so we can start sending code execution to the kernel, etc.
        this._set_state("starting");

        if (this._state === "closed") {
            throw Error("closed");
        }

        // We have now received an iopub or shell message from the kernel,
        // so kernel has started running.
        debug("kernels", "start_running");
        this._set_state("running");
    }

    // Signal should be a string like "SIGINT", "SIGKILL".
    // See https://nodejs.org/api/process.html#process_process_kill_pid_signal
    signal(signal: string): void {
        const spawn = this._kernel != null ? this._kernel.spawn : undefined;
        const pid = spawn?.pid;
        //dbg(`pid=${pid}, signal=${signal}`);
        debug("kernels",`received signal: pid=${pid} signal:${signal}`)
        if (pid == null) return;
        try {
            //this.clear_execute_code_queue();
            process.kill(-pid, signal); // negative to kill the process group
        } catch (err) {
            debug("kernels",`signal error: ${err}`);
        }
    }

    private async ensure_running(): Promise<void> {
        debug("kernels","ensure_running")
        if (this._state == "closed") {
            throw Error("closed so not possible to ensure running");
        }
        if (this._state === "running") {
            return;
        }
        debug("kernels","spawning")
        await this.spawn();
        if (!this.has_ensured_running) {
            debug("kernels","waiting for kernel info");
            this.has_ensured_running = true;
            await this._get_kernel_info();
            debug("kernels","received kernel info");
        }
    }

    // TODO: factor commonalities out of call( ) and shutdown( )
    async shutdown( ): Promise<any> {
        if (!this.has_ensured_running) {
            await this.ensure_running();
        }
        // Do a paranoid double check anyways...
        if (this.channel == null || this._state == "closed") {
            throw Error("not running, so can't call");
        }
        const outgoing = message({msg_type: "shutdown_request", username: this.channel?.header.username, session: this.channel?.header.session}, {restart: false})
        this.channel?.channel.next(outgoing)
        // Wait for the response that has the right msg_id.
        let the_mesg = new Array<any>( )
        const wait_for_response = (cb: any) => {
            const f = (incoming: any) => {
                if (incoming.parent_header.msg_id === outgoing.header.msg_id) {
                    debug("kernels","call( ) received target shell message:",incoming)
                    this.removeListener("shell", f);
                    this.removeListener("iopub", g);
                    this.removeListener("closed", h);
                    incoming = deep_copy(incoming.content);
                    if (len(incoming.metadata) === 0) {
                        delete incoming.metadata;
                    }
                    the_mesg.push({channel: "shell", content: incoming});
                    cb();
                } else {
                    debug("kernels","call( ) received some other shell message:",incoming)
                }
            };
            const g = (incoming: any) => {
                if (incoming.parent_header.msg_id === outgoing.header.msg_id) {
                    debug("kernels","call( ) received target iopub message:",incoming)
                    incoming = deep_copy(incoming.content)
                    the_mesg.push({channel: "iopub", content: incoming})
                } else {
                    debug("kernels","call( ) received some other iopub message:",incoming)
                }
            };
            const h = () => {
                debug("kernels","call( ) received close message")
                this.removeListener("shell", f);
                this.removeListener("iopub", g);
                this.removeListener("closed", h);
                cb("closed");
            };
            this.on("shell", f);
            this.on("iopub", g);
            this.on("closed", h);
        };
        await callback(wait_for_response);
        return the_mesg;
    }

    async call(msg_type: MessageType, content?: any): Promise<any> {
        debug("kernels",`calling kernel: ${msg_type}`)
        if (!this.has_ensured_running) {
            await this.ensure_running();
        }
        // Do a paranoid double check anyways...
        if (this.channel == null || this._state == "closed") {
            throw Error("not running, so can't call");
        }

        // TODO: error check/fill-in content
        const outgoing = message( { msg_type, username: this.channel?.header.username, session: this.channel?.header.session }, content )
        outgoing.channel = "shell"
        debug("kernels","call( ) sending message:",outgoing)

        // Send the message
        this.channel?.channel.next(outgoing);

        // Wait for the response that has the right msg_id.
        let the_mesg = new Array<any>( )
        const wait_for_response = (cb: any) => {
            const f = (incoming: any) => {
                if (incoming.parent_header.msg_id === outgoing.header.msg_id) {
                    debug("kernels","call( ) received target shell message:",incoming)
                    this.removeListener("shell", f);
                    this.removeListener("iopub", g);
                    this.removeListener("closed", h);
                    incoming = deep_copy(incoming.content);
                    if (len(incoming.metadata) === 0) {
                        delete incoming.metadata;
                    }
                    the_mesg.push({channel: "shell", content: incoming});
                    cb();
                } else {
                    debug("kernels","call( ) received some other shell message:",incoming)
                }
            };
            const g = (incoming: any) => {
                if (incoming.parent_header.msg_id === outgoing.header.msg_id) {
                    debug("kernels","call( ) received target iopub message:",incoming)
                    incoming = deep_copy(incoming.content)
                    the_mesg.push({channel: "iopub", content: incoming})
                } else {
                    debug("kernels","call( ) received some other iopub message:",incoming)
                }
            };
            const h = () => {
                debug("kernels","call( ) received close message")
                this.removeListener("shell", f);
                this.removeListener("iopub", g);
                this.removeListener("closed", h);
                cb("closed");
            };
            this.on("shell", f);
            this.on("iopub", g);
            this.on("closed", h);
        };
        await callback(wait_for_response);
        return the_mesg;
    }

    async _get_kernel_info(): Promise<void> {
        /*
          The following is very ugly!  In practice, with testing,
          I've found that some kernels simply
          don't start immediately, and drop early messages.  The only reliable way to
          get things going properly is to just keep trying something (we do the kernel_info
          command) until it works. Only then do we declare the kernel ready for code
          execution, etc.   Probably the jupyter devs never notice this race condition
          bug in ZMQ/Jupyter kernels... or maybe the Python server has a sort of
          accidental work around.

          Update: a Jupyter dev has finally publicly noticed this bug:
          https://github.com/jupyterlab/rtc/pull/73#issuecomment-705775279
        */
        const that = this;
        async function f(): Promise<void> {
            if (that._state == "closed") return;
            debug("kernels",`calling kernel_info_request... ${that._state}`);
            await that.call("kernel_info_request");
            if (that._state === "starting") {
                throw Error("still starting");
            }
        }

        //dbg("getting kernel info to be certain kernel is fully usable...");
        await retry_until_success({
            start_delay: 500,
            max_delay: 5000,
            factor: 1.4,
            max_time: 60000, // long in case of starting many at once --
            // we don't want them to all fail and start
            // again and fail ad infinitum!
            f: f,
            log: function (...args: any[]) {
                debug("kernels",`retry_until_success: ${args}`)
            },
        });
        if (this._state == "closed") {
            throw Error("closed");
        }

        debug("kernels","successfully got kernel info")
    }


};

