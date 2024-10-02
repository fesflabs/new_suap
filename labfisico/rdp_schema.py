rdp_attr_schema = {
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
            "type": "string",
            "title": "Maximum number of connections",
            "description": "Maximum number of connections.",
            "default": "",
            "maxLength": 3
        },
        "max-connections-per-user": {
            "type": "string",
            "title": "Maximum number of connections per user",
            "description": "Maximum number of connections per user.",
            "default": "",
            "maxLength": 3
        },
        "guacd-hostname": {
            "type": "string",
            "title": "Guacd Hostname",
            "description": "The host the Guacamole proxy daemon (guacd) is listening on.",
            "default": "",
        },
        "guacd-port": {
            "id": "properties/attributes/properties/guacd-port",
            "type": "string",
            "title": "Guacd Port",
            "description": "The port the Guacamole proxy daemon (guacd) is listening on.",
            "default": "",
        },
        "guacd-encryption": {
            "id": "properties/attributes/properties/guacd-encryption",
            "type": "string",
            "title": "Guacd Encryption",
            "description": "If enabled, the communication between the web app and guacd will be encrypted",
            "default": "",
            "enum": ["tls"]

        },
        "weight": {
            "id": "properties/attributes/properties/weight",
            "type": "string",
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
rdp_auth_schema = {
    "id": "rdp/properties/parameters/auth",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "required": [
        "username", "password", "domain",
    ],
    "properties": {
        "username": {
            "id": "properties/parameters/properties/username",
            "type": "string",
            "title": "Username",
            "description": "The username to use when attempting authentication, if any.",
            "default": "${GUAC_USERNAME}"
        },
        "password": {
            "id": "properties/parameters/properties/password",
            "type": "string",
            "title": "Password",
            "description": "The password to use when attempting authentication, if any.",
            "default": "${GUAC_PASSWORD}"
        },
        "domain": {
            "id": "properties/parameters/properties/domain",
            "type": "string",
            "title": "Domain",
            "description": "The domain to use when attempting authentication, if any.",
            "default": "ifrn.local"
        },

        "security": {
            "id": "properties/parameters/properties/security",
            "type": "string",
            "title": "Security Mode",
            "description": "The security mode to use for the RDP connection.",
            "default": "nla",
            "enum": ["nla", "rdp", "tls", "vmconnect", "any"]
        },
        "disable-auth": {
            "id": "properties/parameters/properties/disable-auth",
            "type": "boolean",
            "title": "Disable authentication",
            "description": 'If checked, authentication will be disabled',
            "default": "",
            "format": "checkbox"
        },
        "ignore-cert": {
            "id": "properties/parameters/properties/ignore-cert",
            "type": "boolean",
            "title": "Ignore server certificate.",
            "description": 'If checked, the certificate returned by the server will be ignored',
            "default": True,
            "format": "checkbox"
        }
    }
}

rdp_network_schema = {
    "id": "rdp/properties/parameters/network",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "required": [
        "hostname", "port",
    ],
    "properties": {
        "hostname": {
            "id": "rdp/properties/parameters/properties/hostname",
            "type": "string",
            "title": "Hostname",
            "description": "The hostname or IP address of the SSH server Guacamole should connect to.",
            "default": ""
        },
        "port": {
            "id": "properties/parameters/properties/port",
            "type": "string",
            "title": "Port",
            "description": "The port the SSH server is listening on.",
            "default": "3389"
        }
    }
}


rdp_display_schema = {
    "id": "rdp/properties/parameters/display",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "required": [],
    "properties": {
        "read-only": {
            "id": "properties/parameters/properties/read-only",
            "type": "boolean",
            "title": "Read Only",
            "description": "Display Read Only.",
            "default": "",
            "format": "checkbox"
        },
        "width": {
            "id": "properties/parameters/properties/width",
            "type": "string",
            "title": "Display Width",
            "description": "The width of the display to request, in pixels.",
            "default": "1280"
        },
        "height": {
            "id": "properties/parameters/properties/height",
            "type": "string",
            "title": "Display Height",
            "description": "The height of the display to request, in pixels.",
            "default": "720"
        },
        "dpi": {
            "id": "properties/parameters/properties/dpi",
            "type": "string",
            "title": "Resolution (DPI)",
            "description": "The desired effective resolution of the client display.",
            "minimum": 640,
            "default": ""
        },
        "color-depth": {
            "id": "properties/parameters/properties/color-depth",
            "type": "string",
            "title": "Color Depth",
            "description": "The color depth to request, in bits-per-pixel.",
            "default": "",
            "enum": ["8", "16", "24", "32"]
        },
        "resize-method": {
            "id": "properties/parameters/properties/resize-method",
            "type": "string",
            "title": "Resize Method",
            "description": "The method to use to update the RDP server when the width or height of the client display changes.",
            "default": "",
            "enum": ["reconnect", "display-update"]
        },

    }
}

rdp_clipboard_schema = {
    "id": "rdp/properties/parameters/clipboard",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "disable-copy": {
            "id": "properties/parameters/properties/disable-copy",
            "type": "boolean",
            "title": "Disable copying From Remote Desktop",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "disable-paste": {
            "id": "properties/parameters/properties/disable-paste",
            "type": "boolean",
            "title": "Disable Pasting From Client",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
    }
}

rdp_screen_recording_schema = {
    "id": "rdp/properties/parameters/screen_recording",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "recording-path": {
            "id": "properties/parameters/properties/recording-path",
            "type": "string",
            "title": "Recording Path",
            "description": "The directory in which screen recording files should be created.",
            "default": ""
        },
        "recording-name": {
            "id": "properties/parameters/properties/recording-name",
            "type": "string",
            "title": "Recording Name",
            "description": "The filename to use for any created recordings. If omitted, the value “recording” will be used instead.",
            "default": ""
        },
        "recording-exclude-output": {
            "id": "properties/parameters/properties/recording-exclude-output",
            "type": "string",
            "title": "Recording Exclude Ouput",
            "description": 'If set to "true", graphical output and other data normally streamed from server to client will be excluded from the recording.',
            "default": ""
        },
        "recording-exclude-mouse": {
            "id": "properties/parameters/properties/recording-exclude-mouse",
            "type": "string",
            "title": "Recording Exclude Mouse",
            "description": "If true, the user mouse events will be excluded from the recording.",
            "default": ""
        },
        "recording-include-keys": {
            "id": "properties/parameters/properties/recording-include-keys",
            "type": "string",
            "title": "Recording Include Keys",
            "description": 'If set to "true", user key events will be included in the recording.',
            "default": ""
        },
        "create-recording-path": {
            "id": "properties/parameters/properties/create-recording-path",
            "type": "string",
            "title": "Create Recording Path",
            "description": 'If set to “true”, user key events will be included in the recording',
            "default": ""
        },
    }
}

rdp_sftp_schema = {
    "id": "rdp/properties/parameters/sftp",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "enable-sftp": {
            "id": "properties/parameters/properties/enable-sftp",
            "type": "boolean",
            "title": "Enable SFTP",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "sftp-hostname": {
            "id": "properties/parameters/properties/sftp-hostname",
            "type": "string",
            "title": "SFTP Hostname",
            "description": "The hostname or IP address of the server hosting SFTP.",
            "default": ""
        },
        "sftp-port": {
            "id": "properties/parameters/properties/sftp-port",
            "type": "string",
            "title": "SFTP Port",
            "description": "An explanation about the purpose of this instance.",
            "default": ""
        },
        "sftp-username": {
            "id": "properties/parameters/properties/sftp-username",
            "type": "string",
            "title": "SFTP Username",
            "description": "The username to authenticate as when connecting to the specified SSH server for SFTP.",
            "default": ""

        },
        "sftp-password": {
            "id": "properties/parameters/properties/sftp-password",
            "type": "string",
            "title": "SFTP Password",
            "description": "The password to use when authenticating with the specified SSH server for SFTP.",
            "default": ""

        },
        "sftp-host-key": {
            "id": "properties/parameters/properties/sftp-host-key",
            "type": "string",
            "title": "SFTP Host Key",
            "description": "Public host key (Base64)",
            "default": ""

        },
        "sftp-private-key": {
            "id": "properties/parameters/properties/sftp-private-key",
            "type": "string",
            "title": "SFTP Private Key",
            "description": "The entire contents of the private key to use for public key authentication.",
            "default": ""

        },
        "sftp-passphrase": {
            "id": "properties/parameters/properties/sftp-passphrase",
            "type": "string",
            "title": "SFTP Passphrase",
            "description": "The passphrase to use to decrypt the private key for use in public key authentication.",
            "default": ""

        },
        "sftp-root-directory": {
            "id": "properties/parameters/properties/sftp-root-directory",
            "type": "string",
            "title": "SFTP Root Directory",
            "description": "The root directory of the SFTP server.",
            "default": ""

        },
        "sftp-directory": {
            "id": "properties/parameters/properties/sftp-directory",
            "type": "string",
            "title": "SFTP Directory",
            "description": "The directory to upload files to if they are simply dragged and dropped",
            "default": ""
        },

        "sftp-server-alive-interval": {
            "id": "properties/parameters/properties/sftp-server-alive-interval",
            "type": "string",
            "title": "SFTP keepalive interval",
            "description": "The amount of time in seconds before the client will send a signal to the serve",
            "default": ""
        },
    }
}

rdp_device_redirect_schema = {
    "id": "rdp/properties/parameters/device_redirect",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "enable-printing": {
            "id": "properties/parameters/properties/enable-printing",
            "type": "boolean",
            "title": "Enable printing",
            "description": "Printing support requires GhostScript to be installed.",
            "default": "",
            "format": "checkbox"
        },
        "printer-name": {
            "id": "properties/parameters/properties/printer-name",
            "type": "string",
            "title": "Redirected Printer Name",
            "description": "The anme of the redirected printer name.",
            "default": ""
        },
        "enable-drive": {
            "id": "properties/parameters/properties/enable-drive",
            "type": "boolean",
            "title": "Enable Drive",
            "description": "Enable file transfer support to virtual drive",
            "default": "",
            "format": "checkbox"
        },
        "drive-name": {
            "id": "properties/parameters/properties/drive-name",
            "type": "string",
            "title": "Drive Name",
            "description": "The name of the filesystem used when passed through to the RDP session.",
            "default": ""
        },
        "create-drive-path": {
            "id": "properties/parameters/properties/create-drive-path",
            "type": "boolean",
            "title": "Automatically create drive",
            "description": "The path will automatically be created if it does not yet exist.",
            "default": "",
            "format": "checkbox"
        },
        "drive-path": {
            "id": "properties/parameters/properties/drive-path",
            "type": "string",
            "title": "Drive Path",
            "description": "The directory on the Guacamole server in which transferred files should be stored.",
            "default": ""
        },

        "console-audio": {
            "id": "properties/parameters/properties/console-audio",
            "type": "boolean",
            "title": "Support audio in console",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "disable-audio": {
            "id": "properties/parameters/properties/disable-audio",
            "type": "boolean",
            "title": "Disable Audio",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "enable-audio-input": {
            "id": "properties/parameters/properties/enable-audio-input",
            "type": "boolean",
            "title": "Enable audio input (microphone)",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "disable-dowload": {
            "id": "properties/parameters/properties/disable-download",
            "type": "boolean",
            "title": "Disable File Download",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "disable-upload": {
            "id": "properties/parameters/properties/disable-upload",
            "type": "boolean",
            "title": "Disable Upload",
            "description": "",
            "default": "",
            "format": "checkbox"
        },
        "static-channels": {
            "id": "properties/parameters/properties/static-channels",
            "type": "string",
            "title": "Static channel names",
            "description": "A comma-separated list of static channel names to open and expose as pipes",
            "default": ""
        },
    }
}

rdp_performance_schema = {
    "id": "rdp/properties/parameters/performance",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "enable-wallpaper": {
            "id": "properties/parameters/properties/enable-wallpaper",
            "type": "boolean",
            "title": "Enable Wallpaper",
            "description": "Enables rendering of the desktop wallpaper.",
            "default": "",
            "format": "checkbox"
        },
        "enable-theming": {
            "id": "properties/parameters/properties/enable-theming",
            "type": "boolean",
            "title": "Enable Theming",
            "description": "Enables use of theming of windows and controls.",
            "default": "",
            "format": "checkbox"
        },
        "enable-font-smoothing": {
            "id": "properties/parameters/properties/enable-font-smoothing",
            "type": "boolean",
            "title": "Enable-font-smoothing (ClearType)",
            "description": "If enabled, text will be rendered with smooth edges.",
            "default": "",
            "format": "checkbox"
        },
        "enable-full-window-drag": {
            "id": "properties/parameters/properties/enable-full-window-drag",
            "type": "boolean",
            "title": "Enable Full Window Drag",
            "description": "If enabled, the contents of windows will be displayed as windows are moved.",
            "default": "",
            "format": "checkbox"
        },
        "enable-desktop-composition": {
            "id": "properties/parameters/properties/enable-desktop-composition",
            "type": "boolean",
            "title": "Enable Desktop Composition",
            "description": "if enabled, graphical effects such as transparent windows and shadows will be allowed.",
            "default": False,
            "format": "checkbox"
        },
        "enable-menu-animations": {
            "id": "properties/parameters/properties/enable-menu-animations",
            "type": "boolean",
            "title": "Enable Menu Animations",
            "description": "if enabled, menu open and close animations will be allowed.",
            "default": "",
            "format": "checkbox"
        },
        "disable-bitmap-caching": {
            "id": "properties/parameters/properties/disable-bitmap-caching",
            "type": "boolean",
            "title": "Disable Bitmap Caching",
            "description": "if enabled, the RDP bitmap cache will not be used..",
            "default": True,
            "format": "checkbox"
        },
        "disable-offscreen-caching": {
            "id": "properties/parameters/properties/disable-offscreen-caching",
            "type": "boolean",
            "title": "Disable offscreen caching",
            "description": "If enabled, it will disable caching of those regions.",
            "default": True,
            "format": "checkbox"
        },
        "disable-glyph-caching": {
            "id": "properties/parameters/properties/disable-glyph-caching",
            "type": "boolean",
            "title": "Disable Glyph Caching",
            "description": "If enabled, it will disable that glyph caching in the RDP session.",
            "default": True,
            "format": "checkbox"
        },
    }
}

rdp_basic_settings_schema = {
    "id": "rdp/properties/parameters/basci_settings",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "initial-program": {
            "id": "properties/parameters/properties/initial-program",
            "type": "string",
            "title": "Initial Program",
            "description": "The full path to the program to run immediately upon connecting.",
            "default": ""

        },
        "client-name": {
            "id": "properties/parameters/properties/client-name",
            "type": "string",
            "title": "Client Name",
            "description": "The client name that will be used to connect to RDP Server.",
            "default": ""
        },
        "server-layout": {
            "id": "properties/parameters/properties/server-layout",
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
            "id": "properties/parameters/properties/timezone",
            "type": "string",
            "title": "Timezone",
            "description": "The timezone that the client should send to the server.",
            "default": ""
        },

        "console": {
            "id": "properties/parameters/properties/console",
            "type": "string",
            "title": "Console",
            "description": "If enabled, it will be connected to the console (admin) session of the RDP server",
            "default": ""
        }
    }
}

rdp_gateway_schema = {
    "id": "rdp/properties/parameters/basci_settings",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "gateway-hostname": {
            "id": "properties/parameters/properties/gateway-hostname",
            "type": "string",
            "title": "Gateway Hostname",
            "description": "The hostname of the remote desktop gateway.",
            "default": ""
        },
        "gateway-port": {
            "id": "properties/parameters/properties/gateway-port",
            "type": "string",
            "title": "Gateway Port",
            "description": "The port of the remote desktop gateway. By default, this will be 443",
            "default": ""
        },
        "gateway-username": {
            "id": "properties/parameters/properties/gateway-username",
            "type": "string",
            "title": "Gateway Username",
            "description": "The username of the user authenticating with the remote desktop gateway.",
            "default": ""
        },
        "gateway-password": {
            "id": "properties/parameters/properties/gateway-password",
            "type": "string",
            "title": "Gateway Password",
            "description": "The password to provide when authenticating with the remote desktop gateway.",
            "default": ""
        },
        "gateway-domain": {
            "id": "properties/parameters/properties/gateway-domain",
            "type": "string",
            "title": "Gateway Domain",
            "description": "The domain of the user authenticating with the remote desktop gateway.",
            "default": ""
        }
    }
}

rdp_remote_app_schema = {
    "id": "rdp/properties/parameters/remote_app",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "remote-app": {
            "id": "properties/parameters/properties/remote-app",
            "type": "string",
            "title": "Remote App Program",
            "description": "Specifies the remote app to start on the remote desktop.",
            "default": ""
        },
        "remote-app-dir": {
            "id": "properties/parameters/properties/remote-app-dir",
            "type": "string",
            "title": "Remote App Directory",
            "description": "The working directory, if any, for the remote application.",
            "default": ""
        },
        "remote-app-args": {
            "id": "properties/parameters/properties/remote-app-args",
            "type": "string",
            "title": "Remote App Parameters",
            "description": "The command-line arguments, if any, for the remote application.",
            "default": ""
        },
    }
}
rdp_preconnection_schema = {
    "id": "rdp/properties/parameters/preconnection",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "preconnection-id": {
            "id": "properties/parameters/properties/preconnection-id",
            "type": "string",
            "title": "RDP Source ID",
            "description": "The numeric ID of the RDP source.",
            "default": ""
        },
        "preconnection-blob": {
            "id": "properties/parameters/properties/preconnection-blob",
            "type": "string",
            "title": "Preconnection BLOB (VM ID)",
            "description": "An arbitrary string which identifies the RDP source.",
            "default": ""
        }
    }
}

rdp_wol_schema = {
    "id": "rdp/properties/parameters/wol",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "properties": {
        "wol-send-packet": {
            "id": "properties/parameters/properties/wol-send-packet",
            "type": "boolean",
            "title": "Send WoL Packet",
            "description": "If enabled, Guacamole will attempt to send the Wake-On-LAN packet prior to establishing a connection.",
            "default": "",
            "format": "checkbox"
        },
        "wol-mac-addr": {
            "id": "properties/parameters/properties/wol-mac-addr",
            "type": "string",
            "title": "WOL MAC Address",
            "description": "Configures the MAC address that Guacamole will use in the magic WoL packet.",
            "default": ""
        },
        "wol-broadcast-addr": {
            "id": "properties/parameters/properties/wol-broadcast-addr",
            "type": "string",
            "title": "WOL Broadcast Address",
            "description": "Configures the IPv4 broadcast address or IPv6 multicast address.",
            "default": ""
        },
        "wol-udp-port": {
            "id": "properties/parameters/properties/wol-udp-addr",
            "type": "string",
            "title": "WOL UDP Port",
            "description": "Configures the UDP port that will be set in the WoL packet",
            "default": ""
        },
        "wol-wait-time": {
            "id": "properties/parameters/properties/wol-wait-time",
            "type": "string",
            "title": "WOL Wait Time",
            "description": "Number of seconds before attempting the initial connection",
            "default": ""
        }
    }
}

rdp_load_balancing_schema = {
    "id": "rdp/properties/parameters/network",
    "type": "object",
    "title": " ",
    "description": "",
    "default": {},
    "required": [],
    "properties": {
        "load-balance-info": {
            "id": "properties/parameters/properties/load-balance-info",
            "type": "string",
            "title": "Load Balance Info",
            "description": "The load balancing information or cookie which should be provided to the connection broker.",
            "default": ""
        },
        "weight": {
            "id": "properties/attributes/properties/weight",
            "type": "string",
            "title": "Connection Weight",
            "description": "The weight used for applying weighted load balancing",
            "default": "",
        },
        "failover-only": {
            "type": "boolean",
            "title": "Failover Only.",
            "description": "Use for failover only.",
            "default": False,
            "format": "checkbox"
        },
    }
}

rdp_parameters_schema = [
    rdp_network_schema, rdp_auth_schema, rdp_performance_schema,
    rdp_basic_settings_schema, rdp_display_schema, rdp_wol_schema,
    rdp_gateway_schema, rdp_clipboard_schema, rdp_screen_recording_schema,
    rdp_sftp_schema, rdp_device_redirect_schema, rdp_preconnection_schema,
    rdp_load_balancing_schema
]

rdp_schema = {
    'attrs': rdp_attr_schema,
    'parameters': rdp_parameters_schema
}


def extract_schema_from(json_data, keys):
    return {key: json_data.get(key, None) for key in keys}
