from .auth import Auth


class Extenal:
    def __init__(self, auth: Auth) -> None:
        self.auth: Auth = auth

    @property
    def base_endpoint(self):
        return f'{self.auth.REST_API}/external'

    def mount_url(self, endpoint: str, api_version: str = "v1") -> str:
        return f'/external/{api_version}/{endpoint}'

    def get_ad_users_or_groups_by_page(self, page: int, maxpagesize: int, filter: list = "", group_only: bool = True, version="v1") -> list:
        endpoint = '/ad-users-or-groups'
        url = self.mount_url(endpoint, version)
        extra_filter = "group_only={group_only}"
        return self.auth.paginated_request_by_page(url, page, maxpagesize=maxpagesize, filter=filter, extra_filter=extra_filter)

    def get_ad_users_or_groups(self, maxpagesize: int = 100, filter: dict = "", group_only: bool = True, version="v1") -> list:
        """
        Lists the application pools in the environment.
        """
        endpoint = '/ad-users-or-groups'
        url = self.mount_url(endpoint, version)
        return self.auth.paginated_request(url, filter=filter, maxpagesize=maxpagesize)

    def get_ad_users_or_group(self, id: str, version: str = "v1") -> dict:
        """
        Get information related to AD User or Group.
        """
        endpoint = f"ad-users-or-groups/{id}"
        url = self.mount_url(endpoint, version)
        return self.auth.request("GET", url)
