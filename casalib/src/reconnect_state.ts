
export function ReconnectState( ) {
    this.timeout = 1000
    this.retries = 20
    this.connected = true
    this.backoff = ( ) => {
        this.connected = false
        this.timeout += Math.floor(1.8 ** (22 - this.retries))
        this.retries -= 1
    }
}
