attr_schema = {
    "$id": "#/properties/attributes",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "required": [
        "max-connections",
        "max-connections-per-user",
    ],
    "format": "grid",
    "properties": {
        "max-connections": {
            "$id": "#/properties/attributes/properties/max-connections",
            "type": "string",
            "title": "Maximum number of connections",
            "description": "Número máximo de conexões.",
            "default": "",
            "maxLength": 3
        },
        "max-connections-per-user": {
            "$id": "#/properties/attributes/properties/max-connections-per-user",
            "type": "string",
            "title": "Maximum number of connections per user",
            "description": "Número máximo de conexões por usuário.",
            "default": "",
        },
        "guacd-hostname": {
            "$id": "#/properties/attributes/properties/guacd-hostname",
            "type": "string",
            "title": "Guacd Hostname",
            "description": "The host the Guacamole proxy daemon (guacd) is listening on.",
            "default": "",
        },
        "guacd-port": {
            "$id": "#/properties/attributes/properties/guacd-port",
            "type": "string",
            "title": "Guacd Port",
            "description": "The port the Guacamole proxy daemon (guacd) is listening on.",
            "default": "",
        },
        "guacd-encryption": {
            "$id": "#/properties/attributes/properties/guacd-encryption",
            "type": "string",
            "title": "Guacd Encryption",
            "description": "An explanation about the purpose of this instance.",
            "default": "",
            "enum": ["tls"]

        },
        "weight": {
            "$id": "#/properties/attributes/properties/weight",
            "type": "integer",
            "title": "Connection Weight",
            "description": "The weight used for applying weighted load balancing",
            "default": "",
        },
        "failover-only": {
            "type": "boolean",
            "title": "Failover Only.",
            "description": "Use for failover only.",
            "default": "",
            "format": "checkbox"
        },

    },
}

parameters_schema = {
    "$id": "#/properties/parameters",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "required": [
        "username", "password", "domain",
        "port",
    ],
    "properties": {
        # NETWORK
        "hostname": {
            "$id": "#/properties/parameters/properties/hostname",
            "type": "string",
            "title": "Hostname",
            "description": "The hostname or IP address of the SSH server Guacamole should connect to.",
            "default": ""
        },
        "port": {
            "$id": "#/properties/parameters/properties/port",
            "type": "integer",
            "title": "Port",
            "description": "The port the SSH server is listening on.",
            "default": "3389"
        },
        # AUTH
        "username": {
            "$id": "#/properties/parameters/properties/username",
            "type": "string",
            "title": "Username",
            "description": "An explanation about the purpose of this instance.",
            "default": "${GUAC_USERNAME}"
        },
        "password": {
            "$id": "#/properties/parameters/properties/password",
            "type": "string",
            "title": "Password",
            "description": "The password to use when attempting authentication, if any.",
            "default": "${GUAC_PASSWORD}"
        },
        "domain": {
            "$id": "#/properties/parameters/properties/domain",
            "type": "string",
            "title": "Domain",
            "description": "The domain to use when attempting authentication, if any.",
            "default": "ifrn.local"
        },

        "security": {
            "$id": "#/properties/parameters/properties/security",
            "type": "string",
            "title": "Security Mode",
            "description": "The security mode to use for the RDP connection.",
            "default": "nla",
            "enum": ["nla", "rdp", "tls", "vmconnect", "any"]
        },
        "disable-auth": {
            "$id": "#/properties/parameters/properties/disable-auth",
            "type": "boolean",
            "title": "Disable authentication",
            "description": '',
            "default": "",
            "format": "checkbox"
        },
        "ignore-cert": {
            "$id": "#/properties/parameters/properties/ignore-cert",
            "type": "boolean",
            "title": "Ignore server certificate.",
            "description": '',
            "default": "",
            "format": "checkbox"
        },
        # Display settings
        "width": {
            "$id": "#/properties/parameters/properties/width",
            "type": "integer",
            "title": "Display Width",
            "description": "The width of the display to request, in pixels.",
            "default": ""
        },
        "height": {
            "$id": "#/properties/parameters/properties/height",
            "type": "integer",
            "title": "Display Height",
            "description": "The height of the display to request, in pixels.",
            "default": ""
        },
        "dpi": {
            "$id": "#/properties/parameters/properties/dpi",
            "type": "integer",
            "title": "Resolution (DPI)",
            "description": "The desired effective resolution of the client display.",
            "default": ""
        },
        "color-depth": {
            "$id": "#/properties/parameters/properties/color-depth",
            "type": "string",
            "title": "Color Depth",
            "description": "The color depth to request, in bits-per-pixel.",
            "default": "",
            "enum": ["8", "16", "24", "32"]
        },
        "resize-method": {
            "$id": "#/properties/parameters/properties/resize-method",
            "type": "string",
            "title": "Resize Method",
            "description": "The method to use to update the RDP server when the width or height of the client display changes.",
            "default": "",
            "enum": ["reconnect", "display-update"]
        },
        "read-only": {
            "$id": "#/properties/parameters/properties/read-only",
            "type": "boolean",
            "title": "Read Only",
            "description": "Display Read Only.",
            "default": "",
            "format": "checkbox"
        },
        # Clipboard
        # "clipboard-encoding": {
        #     "$id": "#/properties/parameters/properties/clipboard-encoding",
        #     "type": "string",
        #     "title": "",
        #     "description": "The encoding to assume for the VNC clipboard.",
        #     "default": "",
        #     "enum": ["ISO8859-1", "UTF-8", "UTF-16", "CP1252"]
        # },
        "disable-copy": {
            "$id": "#/properties/parameters/properties/disable-copy",
            "type": "boolean",
            "title": "Disable copying From Remote Desktop",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "disable-paste": {
            "$id": "#/properties/parameters/properties/disable-paste",
            "type": "boolean",
            "title": "Disable Pasting From Client",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        #
        # "dest-port": {
        #     "$id": "#/properties/parameters/properties/dest-port",
        #     "type": "string",
        #     "title": "",
        #     "description": "The destination port to request when connecting to a VNC proxy.",
        #     "default": "",
        # },

        # Sceeen Recording
        "recording-path": {
            "$id": "#/properties/parameters/properties/recording-path",
            "type": "string",
            "title": "Recording Path",
            "description": "The directory in which screen recording files should be created.",
            "default": ""
        },
        "recording-name": {
            "$id": "#/properties/parameters/properties/recording-name",
            "type": "string",
            "title": "Recording Name",
            "description": "The filename to use for any created recordings. If omitted, the value “recording” will be used instead.",
            "default": ""
        },
        "recording-exclude-output": {
            "$id": "#/properties/parameters/properties/recording-exclude-output",
            "type": "string",
            "title": "Recording Exclude Ouput",
            "description": 'If set to "true", graphical output and other data normally streamed from server to client will be excluded from the recording.',
            "default": ""
        },
        "recording-exclude-mouse": {
            "$id": "#/properties/parameters/properties/recording-exclude-mouse",
            "type": "string",
            "title": "Recording Exclude Mouse",
            "description": "If true, the user mouse events will be excluded from the recording.",
            "default": ""
        },
        "recording-include-keys": {
            "$id": "#/properties/parameters/properties/recording-include-keys",
            "type": "string",
            "title": "Recording Include Keys",
            "description": 'If set to "true", user key events will be included in the recording.',
            "default": ""
        },
        "create-recording-path": {
            "$id": "#/properties/parameters/properties/create-recording-path",
            "type": "string",
            "title": "Create Recording Path",
            "description": 'If set to “true”, user key events will be included in the recording',
            "default": ""
        },
        ####################################################################################################
        # STFP
        ####################################################################################################
        "enable-sftp": {
            "$id": "#/properties/parameters/properties/enable-sftp",
            "type": "boolean",
            "title": "Enable SFTP",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "sftp-hostname": {
            "$id": "#/properties/parameters/properties/sftp-hostname",
            "type": "string",
            "title": "SFTP Hostname",
            "description": "The hostname or IP address of the server hosting SFTP.",
            "default": ""
        },
        "sftp-port": {
            "$id": "#/properties/parameters/properties/sftp-port",
            "type": "string",
            "title": "SFTP Port",
            "description": "An explanation about the purpose of this instance.",
            "default": ""
        },
        "sftp-username": {
            "$id": "#/properties/parameters/properties/sftp-username",
            "type": "string",
            "title": "SFTP Username",
            "description": "The username to authenticate as when connecting to the specified SSH server for SFTP.",
            "default": ""

        },
        "sftp-password": {
            "$id": "#/properties/parameters/properties/sftp-password",
            "type": "string",
            "title": "SFTP Password",
            "description": "The password to use when authenticating with the specified SSH server for SFTP.",
            "default": ""

        },
        "sftp-host-key": {
            "$id": "#/properties/parameters/properties/sftp-host-key",
            "type": "string",
            "title": "SFTP Host Key",
            "description": "Public host key (Base64)",
            "default": ""

        },
        "sftp-private-key": {
            "$id": "#/properties/parameters/properties/sftp-private-key",
            "type": "string",
            "title": "SFTP Private Key",
            "description": "The entire contents of the private key to use for public key authentication.",
            "default": ""

        },
        "sftp-passphrase": {
            "$id": "#/properties/parameters/properties/sftp-passphrase",
            "type": "string",
            "title": "SFTP Passphrase",
            "description": "The passphrase to use to decrypt the private key for use in public key authentication.",
            "default": ""

        },
        "sftp-root-directory": {
            "$id": "#/properties/parameters/properties/sftp-root-directory",
            "type": "string",
            "title": "SFTP Root Directory",
            "description": "The root directory of the SFTP server.",
            "default": ""

        },
        "sftp-directory": {
            "$id": "#/properties/parameters/properties/sftp-directory",
            "type": "string",
            "title": "SFTP Directory",
            "description": "The directory to upload files to if they are simply dragged and dropped",
            "default": ""
        },

        "sftp-server-alive-interval": {
            "$id": "#/properties/parameters/properties/sftp-server-alive-interval",
            "type": "integer",
            "title": "SFTP keepalive interval",
            "description": "The amount of time in seconds before the client will send a signal to the serve",
            "default": ""
        },
        ####################################################################################################
        # Device redirection
        ####################################################################################################
        "console-audio": {
            "$id": "#/properties/parameters/properties/console-audio",
            "type": "boolean",
            "title": "Support audio in console",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "disable-audio": {
            "$id": "#/properties/parameters/properties/disable-audio",
            "type": "boolean",
            "title": "Disable Audio",
            "description": "An explanation about the purpose of this instance.",
            "default": "",
            "format": "checkbox"
        },
        "enable-audio-input": {
            "$id": "#/properties/parameters/properties/enable-audio-input",
            "type": "boolean",
            "title": "Enable audio input (microphone)",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "enable-printing": {
            "$id": "#/properties/parameters/properties/enable-printing",
            "type": "boolean",
            "title": "Enable printing",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "printer-name": {
            "$id": "#/properties/parameters/properties/printer-name",
            "type": "string",
            "title": "Printer Name",
            "description": "Redirected printer name.",
            "default": ""
        },
        "enable-drive": {
            "$id": "#/properties/parameters/properties/enable-drive",
            "type": "boolean",
            "title": "Enable Drive",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "drive-name": {
            "$id": "#/properties/parameters/properties/drive-name",
            "type": "string",
            "title": "Drive Name",
            "description": "The name of the filesystem used when passed through to the RDP session.",
            "default": ""
        },
        "create-drive-path": {
            "$id": "#/properties/parameters/properties/create-drive-path",
            "type": "boolean",
            "title": "Automatically create drive",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "drive-path": {
            "$id": "#/properties/parameters/properties/drive-path",
            "type": "string",
            "title": "Drive Path",
            "description": "The directory on the Guacamole server in which transferred files should be stored.",
            "default": ""
        },

        "static-channels": {
            "$id": "#/properties/parameters/properties/static-channels",
            "type": "string",
            "title": "Static channel names",
            "description": "A comma-separated list of static channel names to open and expose as pipes",
            "default": ""
        },
        ###############################################################################################
        # PERFORMANCE
        ###############################################################################################
        ###############################################################################################
        # Loading Balance Information
        ###############################################################################################
        "load-balance-info": {
            "$id": "#/properties/parameters/properties/load-balance-info",
            "type": "string",
            "title": "Load Balance Info",
            "description": "The load balancing information or cookie which should be provided to the connection broker.",
            "default": ""
        },
        "enable-wallpaper": {
            "$id": "#/properties/parameters/properties/enable-wallpaper",
            "type": "boolean",
            "title": "Enable Wallpaper",
            "description": "Enables rendering of the desktop wallpaper.",
            "default": "",
            "format": "checkbox"
        },
        "enable-theming": {
            "$id": "#/properties/parameters/properties/enable-theming",
            "type": "boolean",
            "title": "Enable Theming",
            "description": "Enables use of theming of windows and controls.",
            "default": "",
            "format": "checkbox"
        },
        "enable-font-smoothing": {
            "$id": "#/properties/parameters/properties/enable-font-smoothing",
            "type": "boolean",
            "title": "Enable-font-smoothing (ClearType)",
            "description": "If enabled, text will be rendered with smooth edges.",
            "default": "",
            "format": "checkbox"
        },
        "enable-full-window-drag": {
            "$id": "#/properties/parameters/properties/enable-full-window-drag",
            "type": "boolean",
            "title": "Enable Full Window Drag",
            "description": "If enabled, the contents of windows will be displayed as windows are moved.",
            "default": "",
            "format": "checkbox"
        },
        "enable-desktop-composition": {
            "$id": "#/properties/parameters/properties/enable-desktop-composition",
            "type": "boolean",
            "title": "Enable Desktop Composition",
            "description": "if enabled, graphical effects such as transparent windows and shadows will be allowed.",
            "default": False,
            "format": "checkbox"
        },
        "enable-menu-animations": {
            "$id": "#/properties/parameters/properties/enable-menu-animations",
            "type": "boolean",
            "title": "Enable Menu Animations",
            "description": "if enabled, menu open and close animations will be allowed.",
            "default": "",
            "format": "checkbox"
        },
        "disable-bitmap-caching": {
            "$id": "#/properties/parameters/properties/disable-bitmap-caching",
            "type": "boolean",
            "title": "Disable Bitmap Caching",
            "description": "if enabled, the RDP bitmap cache will not be used..",
            "default": True,
            "format": "checkbox"
        },
        "disable-offscreen-caching": {
            "$id": "#/properties/parameters/properties/disable-offscreen-caching",
            "type": "boolean",
            "title": "Disable offscreen caching",
            "description": "If enabled, it will disable caching of those regions.",
            "default": True,
            "format": "checkbox"
        },
        "disable-glyph-caching": {
            "$id": "#/properties/parameters/properties/disable-glyph-caching",
            "type": "boolean",
            "title": "Disable Glyph Caching",
            "description": "If enabled, it will disable that glyph caching in the RDP session.",
            "default": True,
            "format": "checkbox"
        },
        ###############################################################################################
        # Basic Settings
        ###############################################################################################
        "initial-program": {
            "$id": "#/properties/parameters/properties/initial-program",
            "type": "string",
            "title": "Initial Program",
            "description": "The full path to the program to run immediately upon connecting.",
            "default": ""

        },
        "client-name": {
            "$id": "#/properties/parameters/properties/client-name",
            "type": "string",
            "title": "Client Name",
            "description": "The client name that will be used to connect to RDP Server.",
            "default": ""
        },
        "server-layout": {
            "$id": "#/properties/parameters/properties/server-layout",
            "type": "string",
            "title": "Keyboard Layout",
            "description": "An explanation about the purpose of this instance.",
            "default": "pt-br-qwerty",
            "enum": [
                "de-ch-qwertz", "de-de-qwertz", "en-gb-qwerty",
                "en-us-qwerty", "es-es-qwerty", "es-latam-qwerty",
                "failsafe", "fr-be-azerty", "fr-fr-azerty",
                "fr-ch-qwertz", "hu-hu-qwertz", "it-it-qwerty",
                "ja-jp-qwerty", "no-no-qwerty", "pt-br-qwerty",
                "sv-se-qwerty", "da-dk-qwerty", "tr-tr-qwerty"
            ]
        },

        "timezone": {
            "$id": "#/properties/parameters/properties/timezone",
            "type": "string",
            "title": "Timezone",
            "description": "The timezone that the client should send to the server.",
            "default": ""
        },

        "console": {
            "$id": "#/properties/parameters/properties/console",
            "type": "string",
            "title": "Console",
            "description": "If enabled, it will be connected to the console (admin) session of the RDP server",
            "default": ""
        },
        ###############################################################################################
        # Gateway
        ###############################################################################################
        "gateway-hostname": {
            "$id": "#/properties/parameters/properties/gateway-hostname",
            "type": "string",
            "title": "Gateway Hostname",
            "description": "The hostname of the remote desktop gateway.",
            "default": ""
        },
        "gateway-port": {
            "$id": "#/properties/parameters/properties/gateway-port",
            "type": "integer",
            "title": "Gateway Port",
            "description": "The port of the remote desktop gateway. By default, this will be 443",
            "default": ""
        },
        "gateway-username": {
            "$id": "#/properties/parameters/properties/gateway-username",
            "type": "string",
            "title": "Gateway Username",
            "description": "The username of the user authenticating with the remote desktop gateway.",
            "default": ""
        },
        "gateway-password": {
            "$id": "#/properties/parameters/properties/gateway-password",
            "type": "string",
            "title": "Gateway Password",
            "description": "The password to provide when authenticating with the remote desktop gateway.",
            "default": ""
        },
        "gateway-domain": {
            "$id": "#/properties/parameters/properties/gateway-domain",
            "type": "string",
            "title": "Gateway Domain",
            "description": "The domain of the user authenticating with the remote desktop gateway.",
            "default": ""
        },
        ###############################################################################################
        # RemoteApp
        ###############################################################################################
        "remote-app": {
            "$id": "#/properties/parameters/properties/remote-app",
            "type": "string",
            "title": "Remote App Program",
            "description": "Specifies the remote app to start on the remote desktop.",
            "default": ""
        },
        "remote-app-dir": {
            "$id": "#/properties/parameters/properties/remote-app-dir",
            "type": "string",
            "title": "Remote App Directory",
            "description": "The working directory, if any, for the remote application.",
            "default": ""
        },
        "remote-app-args": {
            "$id": "#/properties/parameters/properties/remote-app-args",
            "type": "string",
            "title": "Remote App Parameters",
            "description": "The command-line arguments, if any, for the remote application.",
            "default": ""
        },

        ################################################################################################################
        # Preconnection PDU / Hyper-V
        ################################################################################################################
        "preconnection-id": {
            "$id": "#/properties/parameters/properties/preconnection-id",
            "type": "string",
            "title": "RDP Source ID",
            "description": "The numeric ID of the RDP source.",
            "default": ""
        },

        "preconnection-blob": {
            "$id": "#/properties/parameters/properties/preconnection-blob",
            "type": "string",
            "title": "Preconnection BLOB (VM ID)",
            "description": "An arbitrary string which identifies the RDP source.",
            "default": ""
        },
        ################################################################################################################
        # Wake-on-LAN (WoL)
        ################################################################################################################
        "wol-send-packet": {
            "$id": "#/properties/parameters/properties/wol-send-packet",
            "type": "boolean",
            "title": "Send WoL Packet",
            "description": "If enabled, Guacamole will attempt to send the Wake-On-LAN packet prior to establishing a connection.",
            "default": "",
            "format": "checkbox"
        },
        "wol-mac-addr": {
            "$id": "#/properties/parameters/properties/wol-mac-addr",
            "type": "string",
            "title": "WOL MAC Address",
            "description": "Configures the MAC address that Guacamole will use in the magic WoL packet.",
            "default": ""
        },
        "wol-broadcast-addr": {
            "$id": "#/properties/parameters/properties/wol-broadcast-addr",
            "type": "string",
            "title": "WOL Broadcast Address",
            "description": "Configures the IPv4 broadcast address or IPv6 multicast address.",
            "default": ""
        },
        "wol-udp-port": {
            "$id": "#/properties/parameters/properties/wol-udp-addr",
            "type": "integer",
            "title": "WOL UDP Port",
            "description": "Configures the UDP port that will be set in the WoL packet",
            "default": ""
        },
        "wol-wait-time": {
            "$id": "#/properties/parameters/properties/wol-wait-time",
            "type": "integer",
            "title": "WOL Wait Time",
            "description": "Number of seconds before attempting the initial connection",
            "default": ""
        },
    },
}

rdp_schema = {
    "$id": "http://example.com/example.json",
    "type": "object",
    "title": "Guacamole Connection Schema",
    "description": "",
    "default": {},
    "required": [
        "name",
        "protocol"
    ],
    "properties": {
        "name": {
            "$id": "#/properties/name",
            "type": "string",
            "title": "Nome",
            "description": "Nome da conexão",
            "default": "",
        },
        "protocol": {
            "$id": "#/properties/protocol",
            "type": "string",
            "title": "Protocolo",
            "description": "Protocolo",
            "enum": ["rdp"],
            "default": "rdp",
        }
    }
}

connection_schema = {
    "$id": "http://example.com/example.json",
    "type": "object",
    "title": "Guacamole Connection Schema",
    "description": "",
    "default": {},
    "required": [
        "name",
        # "identifier",
        # "parentIdentifier",
        "protocol",
        "attributes",
        "parameters"
    ],
    "properties": {
        "name": {
            "$id": "#/properties/name",
            "type": "string",
            "title": "Nome",
            "description": "Nome da conexão",
            "default": "",
        },
        # "identifier": {
        #     "$id": "#/properties/identifier",
        #     "type": "string",
        #     "title": "The identifier schema",
        #     "description": "An explanation about the purpose of this instance.",
        #     "default": "",
        # },
        # "parentIdentifier": {
        #     "$id": "#/properties/parentIdentifier",
        #     "type": "string",
        #     "title": "The parentIdentifier schema",
        #     "description": "An explanation about the purpose of this instance.",
        #     "default": "",

        # },
        "protocol": {
            "$id": "#/properties/protocol",
            "type": "string",
            "title": "Protocolo",
            "description": "Protocolo",
            "enum": ["rdp"],
            "default": "rdp",
        },

        "attributes": attr_schema,
        "parameters": parameters_schema
    },

}
