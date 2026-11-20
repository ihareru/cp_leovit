import base64
import getpass
import ssl
import urllib.error
import urllib.parse
import urllib.request

from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate, make_msgid


SERVER = (
    "https://mail.leovit.ru"
    "/Microsoft-Server-ActiveSync"
)

USERNAME = r"LEOVIT\cpservice"

PROTOCOL_VERSION = "12.1"
DEVICE_ID = "LeovitPortalTest001"
DEVICE_TYPE = "LeovitPortal"

TIMEOUT = 30


class NoRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        return None


def main():
    print("Exchange ActiveSync")
    print(f"Сервер: {SERVER}")
    print(f"Пользователь: {USERNAME}")
    print(f"Версия протокола: {PROTOCOL_VERSION}")
    print()

    password = getpass.getpass(
        "Пароль Exchange: "
    )

    sender = input(
        "Email отправителя: "
    ).strip()

    recipient = input(
        "Email получателя: "
    ).strip()

    if not password or not sender or not recipient:
        print("Не заполнены обязательные поля.")
        return

    message = EmailMessage(policy=SMTP)

    message["From"] = sender
    message["To"] = recipient

    message["Subject"] = (
        "Leovit Portal — тест ActiveSync"
    )

    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()

    message.set_content(
        "Тестовое письмо корпоративного портала.\n\n"
        "Отправлено через Exchange ActiveSync.\n"
        "Протокол: HTTPS.\n"
        "Порт: 443.\n"
        "Версия ActiveSync: 12.1.\n\n"
        "Leovit Portal",
        charset="utf-8",
    )

    credentials = base64.b64encode(
        f"{USERNAME}:{password}".encode("utf-8")
    ).decode("ascii")

    params = urllib.parse.urlencode({
        "Cmd": "SendMail",
        "User": USERNAME,
        "DeviceId": DEVICE_ID,
        "DeviceType": DEVICE_TYPE,
        "SaveInSent": "",
    })

    url = f"{SERVER}?{params}"

    headers = {
        "Authorization": f"Basic {credentials}",
        "MS-ASProtocolVersion": PROTOCOL_VERSION,
        "Content-Type": "message/rfc822",
        "User-Agent": "LeovitPortal/1.0",
    }

    request = urllib.request.Request(
        url=url,
        data=message.as_bytes(policy=SMTP),
        headers=headers,
        method="POST",
    )

    context = ssl.create_default_context()

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(
            context=context,
        ),
        NoRedirectHandler(),
    )

    print()
    print("Отправка письма...")

    try:
        with opener.open(
            request,
            timeout=TIMEOUT,
        ) as response:

            body = response.read()

            print(
                f"HTTP status: {response.status}"
            )

            print("Response headers:")
            print(response.headers)

            if body:
                print("Response body:")
                print(body)

            if response.status == 200 and not body:
                print(
                    "Exchange принял сообщение."
                )
                print(
                    "Проверьте почтовый ящик "
                    "получателя."
                )
            else:
                print(
                    "Требуется проверить "
                    "ответ сервера."
                )

    except urllib.error.HTTPError as exc:
        print(f"HTTP error: {exc.code}")
        print(f"Reason: {exc.reason}")
        print(exc.headers)

        body = exc.read()

        if body:
            print("Response body:")
            print(body)

    except urllib.error.URLError as exc:
        print(
            f"Connection error: {exc.reason}"
        )

    except TimeoutError:
        print(
            "Превышено время ожидания ответа."
        )


if __name__ == "__main__":
    main()
