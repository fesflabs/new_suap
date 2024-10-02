RDP_CONNECTION_PARAMETERS = {
    "port": "3389",
    "read-only": "",
    "swap-red-blue": "",
    "cursor": "",
    "color-depth": "",
    "clipboard-encoding": "",
    "disable-copy": "",
    "disable-paste": "",
    "dest-port": "",
    "recording-exclude-output": "",
    "recording-exclude-mouse": "",
    "recording-include-keys": "",
    "create-recording-path": "",
    "enable-sftp": "",
    "sftp-port": "",
    "sftp-server-alive-interval": "",
    "enable-audio": "",
    "security": "nla",
    "disable-auth": "",
    "ignore-cert": 'true',
    "gateway-port": "",
    "server-layout": 'pt-br-qwerty',  # The server-side keyboard layout.
    "timezone": "",
    "console": "",
    "width": "",
    "height": "",
    "dpi": "",
    "resize-method": "",
    "console-audio": "",
    "disable-audio": "",
    "enable-audio-input": "",
    "enable-printing": "",
    "enable-drive": "",
    "create-drive-path": "",
    "enable-wallpaper": "",
    "enable-theming": "",
    "enable-font-smoothing": "",
    "enable-full-window-drag": "",
    "enable-desktop-composition": "",
    "enable-menu-animations": "",
    "disable-bitmap-caching": 'true',
    "disable-offscreen-caching": 'true',
    "disable-glyph-caching": 'true',
    "preconnection-id": "",
    "hostname": "",
    "username": "",
    "password": "",
    "domain": "",
    "gateway-hostname": "",
    "gateway-username": "",
    "gateway-password": "",
    "gateway-domain": "",
    "initial-program": "",
    "client-name": "",
    "printer-name": "",
    "drive-name": "",
    "drive-path": "",
    "static-channels": "",
    "remote-app": "",
    "remote-app-dir": "",
    "remote-app-args": "",
    "preconnection-blob": "",
    "load-balance-info": "",
    "recording-path": "",
    "recording-name": "",
    "sftp-hostname": "",
    "sftp-host-key": "",
    "sftp-username": "",
    "sftp-password": "",
    "sftp-private-key": "",
    "sftp-passphrase": "",
    "sftp-root-directory": "",
    "sftp-directory": "",
    'wol-send-packet': 'false'  # wake on lan
}

RDP_CONNECTION_ATTRS = {
    "max-connections": "",
    "max-connections-per-user": "",
    "weight": "",
    "failover-only": "",
    "guacd-port": "",
    "guacd-encryption": "",
    "guacd-hostname": "",
}
RDP_CONNECTION = {
    "name": "",
    "identifier": "",
    "parentIdentifier": "ROOT",
    "protocol": "rdp",
    "attributes": RDP_CONNECTION_ATTRS,
    "parameters": RDP_CONNECTION_PARAMETERS,
    "activeConnections": 0,

}

VNC_CONNECTION = {
    "parentIdentifier": "ROOT",
    "name": "",
    "protocol": "vnc",
    "parameters": {
        "port": "5900",
        "read-only": "",
        "swap-red-blue": "",
        "cursor": "",
        "color-depth": "",
        "clipboard-encoding": "",
        "dest-port": "",
        "create-recording-path": "",
        "enable-sftp": "",
        "sftp-port": "",
        "sftp-server-alive-interval": "",
        "enable-audio": "",
        "hostname": "",
        "password": "",
    },
    "attributes": {
        "max-connections": "",
        "max-connections-per-user": "",
        "weight": "",
        "failover-only": "",
        "guacd-port": "",
        "guacd-encryption": "",
        "guacd-hostname": "",
    },
}

SSH_CONNECTION = {
    "activeConnections": 0,
    "attributes": {"max-connections": "", "max-connections-per-user": ""},
    "identifier": "",
    "name": "",
    "parameters": {
        "hostname": "",
        "password": "",
        "port": "22",
        "username": "",
    },
    "parentIdentifier": "ROOT",
    "protocol": "ssh",
}

USER = {
    "username": "",
    "password": "",
    "attributes": {
        "disabled": "",
        "expired": "",
        "access-window-start": "",
        "access-window-end": "",
        "valid-from": "",
        "valid-until": "",
        "timezone": "",
    },
}

ORG_CONNECTION_GROUP = {
    "parentIdentifier": "ROOT",
    "name": "",
    "type": "ORGANIZATIONAL",
    "attributes": {
        "max-connections": "",
        "max-connections-per-user": "",
        "enable-session-affinity": "true"
    },
}

BALACING_CONNECTION_GROUP = {
    "parentIdentifier": "ROOT",
    "name": "",
    "type": "BALANCING",
    "attributes": {
        "max-connections": "1",
        "max-connections-per-user": "1"
    },
}

SYSTEM_PERMISSIONS = [
    {"op": "add", "path": "/systemPermissions", "value": "ADMINISTER"}
]

ADD_READ_PERMISSION = {
    "op": "add",
    "path": "",
    "value": "READ"
}

LDAP_GROUP = {
    "identifier": "",
    "attributes": {"disabled": None}
}


def make_rdp_connection_payload(**kwargs):

    #
    RDP_CONNECTION = {
        "name": kwargs["connection_name"],
        "identifier": "",
        "parentIdentifier": kwargs.get("location", "ROOT"),
        "protocol": "rdp",
        "attributes": {
            "max-connections": kwargs["max_connections"],
            "max-connections-per-user": kwargs["max_connections_per_user"],
            "weight": kwargs.get("weight", ""),
            "failover-only": kwargs.get("failover_only", ""),
            "guacd-port": kwargs.get("guacd-oport", ""),
            "guacd-encryption": kwargs.get("guacd-encryption", ""),
            "guacd-hostname": kwargs.get("guacd-hostname", ""),
        },
        "activeConnections": 0,
        "parameters": {
            # Network
            "hostname": kwargs["hostname"],
            "port": kwargs.get("port", 3389),
            # AUTH
            "username": kwargs["username"],
            "password": kwargs["password"],
            "domain": kwargs["domain"],
            "security": kwargs.get("security", "nla"),
            "disable-auth": kwargs.get("disable-auth", ""),
            "ignore-cert": kwargs.get("ignore_cert", True),
            # Remote Desktop Gateway
            "gateway-hostname": kwargs.get("gateway_hostname", ""),
            "gateway-username": kwargs.get("gateway_username", ""),
            "gateway-password": kwargs.get("gateway_password", ""),
            "gateway-domain": kwargs.get("gateway_domain", ""),
            "gateway-port": "",
            # Basic Settings
            "initial-program": "",
            "client-name": "",
            # The server-side keyboard layout.
            "server-layout": 'pt-br-qwerty',
            #
            "read-only": "",
            "swap-red-blue": "",
            "cursor": "",
            "color-depth": "",
            "clipboard-encoding": "",
            "disable-copy": "",
            "disable-paste": "",
            "dest-port": "",
            "recording-exclude-output": "",
            "recording-exclude-mouse": "",
            "recording-include-keys": "",
            "create-recording-path": "",
            "enable-sftp": "",
            "sftp-port": "",
            "sftp-server-alive-interval": "",
            "enable-audio": "",
            "timezone": "",
            "console": "",
            "width": "",
            "height": "",
            "dpi": "",
            "resize-method": "",
            "console-audio": "",
            "disable-audio": "",
            "enable-audio-input": "",
            "enable-printing": "",
            "enable-drive": "",
            "create-drive-path": "",
            "enable-wallpaper": "",
            "enable-theming": "",
            "enable-font-smoothing": "",
            "enable-full-window-drag": "",
            "enable-desktop-composition": "",
            "enable-menu-animations": "",
            "disable-bitmap-caching": 'true',
            "disable-offscreen-caching": 'true',
            "disable-glyph-caching": 'true',
            "preconnection-id": "",

            "printer-name": "",
            "drive-name": "",
            "drive-path": "",
            "static-channels": "",
            "remote-app": "",
            "remote-app-dir": "",
            "remote-app-args": "",
            "preconnection-blob": "",
            "load-balance-info": "",
            "recording-path": "",
            "recording-name": "",
            "sftp-hostname": "",
            "sftp-host-key": "",
            "sftp-username": "",
            "sftp-password": "",
            "sftp-private-key": "",
            "sftp-passphrase": "",
            "sftp-root-directory": "",
            "sftp-directory": "",
            'wol-send-packet': 'false'  # wake on lan
        },
    }
    return RDP_CONNECTION
