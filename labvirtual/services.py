from typing import Dict
from django.conf import settings
from .vmware_horizon import VMwareHorizonAPI


def make_horizon_from_settings(name='default') -> VMwareHorizonAPI:
    vdi_server = settings.VDI_SERVERS[name]
    creds = dict(
        hostname=vdi_server["HOSTNAME"],
        username=vdi_server["USER"],
        password=vdi_server["PASSWORD"],
        domain=vdi_server["DOMAIN"]
    )
    return VMwareHorizonAPI(**creds)


class DesktopPool:
    def __init__(self, *args, **kwargs) -> None:
        pass


class VMWareHorizonService:
    def __init__(self, hostname, username, password, domain) -> None:
        self.api: VMwareHorizonAPI = VMwareHorizonAPI(hostname=hostname, username=username, password=password, domain=domain)

    @classmethod
    def from_dict(cls, dict):
        return VMWareHorizonService(**dict)

    @classmethod
    def from_settings(cls, name='default'):
        vdi_server = settings.VDI_SERVERS[name]
        creds = dict(
            hostname=vdi_server["HOSTNAME"],
            username=vdi_server["USER"],
            password=vdi_server["PASSWORD"],
            domain=vdi_server["DOMAIN"]
        )
        return VMWareHorizonService(**creds)

    ######################################################
    # AD Domain
    ######################################################
    def get_user_or_ad_group(self, name):
        filter = {
            "type": "Equals",
            "name": "name",
            "value": name,
        }
        groups = self.api.external.get_ad_users_or_groups(filter=filter)
        return groups

    ######################################################
    # Desktop Pool
    ######################################################
    def number_max_of_mahcines(self, desktop_pool_id) -> int:
        desktop_pool = self.api.inventory.get_desktop_pool(desktop_pool_id=desktop_pool_id)
        return desktop_pool['pattern_naming_settings']['max_number_of_machines']

    def get_desktop_pool(self, desktop_pool_id) -> Dict:
        desktop_pool = self.api.inventory.get_desktop_pool(desktop_pool_id=desktop_pool_id)
        return desktop_pool

    def get_desktop_pools(self):
        desktop_pools = self.api.inventory.get_desktop_pools()
        return desktop_pools

    def get_machines_from_desktop_pool(self, desktop_pool_id):
        filter = {
            "type": "Equals",
            "name": "desktop_pool_id",
            "value": desktop_pool_id,
        }
        machines = self.api.inventory.get_machines(filter=filter)
        return machines

    def get_users(self, users):
        ad_user_or_group_ids = []
        for user in users:
            ad_user_or_group_ids.append(self.get_user_or_ad_group(user)[0])
        return ad_user_or_group_ids

    def get_ad_groups_from_desktop_pool(self, desktop_pool_id):
        entitlement = self.api.entitlements.get_desktop_pool_entitlement(desktop_pool_id=desktop_pool_id)
        groups = entitlement["ad_user_or_group_ids"]
        filters = [{"type": "Equals", "name": "id", "value": id} for id in groups]
        filter = {
            "type": "Or",
            "filters": filters
        }
        ad_groups = self.api.external.get_ad_users_or_groups(filter=filter)
        return ad_groups

    def assign_user_or_group_to_desktop_pool(self, name, desktop_pool_id):
        groups = self.get_user_or_ad_group(name)
        ad_user_or_group_ids = [group["id"] for group in groups]
        desktop_pool_data = [
            {'ad_user_or_group_ids': ad_user_or_group_ids, "id": desktop_pool_id}
        ]
        self.api.entitlements.new_desktop_pools_entitlements(desktop_pool_data)

    def remove_user_or_group_from_desktop_pool(self, group_name, desktop_pool_id):
        groups = self.get_user_or_ad_group(group_name)
        ad_user_or_group_ids = [group["id"] for group in groups]
        desktop_pool_data = [
            {'ad_user_or_group_ids': ad_user_or_group_ids, "id": desktop_pool_id}
        ]
        self.api.entitlements.delete_desktop_pools_entitlements(desktop_pool_data)

    def assign_users_to_desktop_pool(self, users, desktop_pool_id):
        ad_user_or_group_ids = [user["id"] for user in self.get_users(users)]
        if ad_user_or_group_ids:
            desktop_pool_data = [
                {'ad_user_or_group_ids': ad_user_or_group_ids, "id": desktop_pool_id}
            ]
            self.api.entitlements.new_desktop_pools_entitlements(desktop_pool_data)

    def get_sessions_from_desktop_pool(self, desktop_pool_id):
        filter = {
            "type": "Equals",
            "name": "desktop_pool_id",
            "value": desktop_pool_id,
        }
        sessions = self.api.inventory.get_sessions(filter=filter)
        return sessions

    def disconnect_sessions_from_desktop_pool(self, desktop_pool_id):
        sessions = self.get_sessions_from_desktop_pool(desktop_pool_id)
        sessions_id = [session["id"] for session in sessions]
        if sessions_id:
            self.api.inventory.disconnect_sessions(session_ids=sessions_id)

    def send_message_to_desktop_pool(self, desktop_pool_id, message):
        sessions = self.get_sessions_from_desktop_pool(desktop_pool_id)
        sessions_id = [session["id"] for session in sessions]
        if sessions_id:
            self.api.inventory.send_message_sessions(session_ids=sessions_id, message=message)
