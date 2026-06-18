class SocialExportService:

    @staticmethod
    def build_exports(
        title: str,
        description: str,
        hashtags: list
    ):

        tags = " ".join(hashtags)

        youtube = {
            "title": title,
            "description": (
                f"{description}\n\n"
                f"{tags}"
            )
        }

        instagram = {
            "caption": (
                f"{title}\n\n"
                f"{description}\n\n"
                f"{tags}"
            )
        }

        tiktok = {
            "caption": (
                f"{title}\n\n"
                f"{tags}"
            )
        }

        return {
            "youtube": youtube,
            "instagram": instagram,
            "tiktok": tiktok
        }