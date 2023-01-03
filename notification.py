from discord import Webhook, RequestsWebhookAdapter

from settings import CONFIG


class Noti:
    def __init__(self, msg, ENV_WEBHOOK: str = CONFIG.ENV_NOTI) -> None:
        self.url = ENV_WEBHOOK
        self.msg = msg

    def send(self):
        if CONFIG.IS_NOTI:
            webhook = Webhook.from_url(self.url, adapter=RequestsWebhookAdapter())
            webhook.send(self.msg)


if __name__ == "__main__":
    Noti("1st").send()
