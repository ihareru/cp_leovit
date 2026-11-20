
import ipaddress

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def parse_ip(value):
    """
    Безопасное преобразование IP-адреса.
    """

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value or "%" in value:
        return None

    try:
        address = ipaddress.ip_address(value)

    except ValueError:
        return None

    if isinstance(
        address,
        ipaddress.IPv6Address,
    ):
        if address.ipv4_mapped is not None:
            address = address.ipv4_mapped

    return address


def get_trusted_proxy_networks():
    """
    Получение списка доверенных сетей.
    """

    raw_networks = getattr(
        settings,
        "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS",
        [],
    )

    networks = []

    for value in raw_networks:

        try:
            network = ipaddress.ip_network(
                value.strip(),
                strict=True,
            )

        except (ValueError, AttributeError) as exc:

            raise ImproperlyConfigured(
                "Invalid trusted proxy network."
            ) from exc

        if network.prefixlen == 0:

            raise ImproperlyConfigured(
                "Trusting all proxy addresses "
                "is not allowed."
            )

        networks.append(network)

    return networks


def is_trusted_proxy(address):
    """
    Проверка принадлежности IP
    к доверенной сети.
    """

    if address is None:
        return False

    for network in get_trusted_proxy_networks():

        if address.version != network.version:
            continue

        if address in network:
            return True

    return False


def get_client_ip(request):
    """
    Определение реального IP клиента.

    X-Real-IP используется только при запросе
    от доверенного прокси.

    X-Forwarded-For намеренно игнорируется.
    """

    remote_address = parse_ip(
        request.META.get(
            "REMOTE_ADDR",
            "",
        )
    )

    if remote_address is None:
        return "unknown"

    if not is_trusted_proxy(remote_address):
        return str(remote_address)

    forwarded_address = parse_ip(
        request.META.get(
            "HTTP_X_REAL_IP",
            "",
        )
    )

    if forwarded_address is None:
        return "unknown"

    return str(forwarded_address)
