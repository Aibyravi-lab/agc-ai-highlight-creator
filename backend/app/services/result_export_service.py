import json

from app.services.job_storage_service import JobStorageService


class ResultExportService:

    @classmethod
    def save_result(
        cls,
        metadata: dict,
        job_id: str | None = None
    ):

        resolved_job_id = (
            JobStorageService.resolve_job_id(job_id)
        )

        output_dir = (
            JobStorageService.subfolder(
                resolved_job_id,
                "results"
            )
        )

        output_file = (
            output_dir /
            "result.json"
        )

        export_data = {

            "title":
            metadata.get(
                "title",
                metadata.get(
                    "reel_title",
                    ""
                )
            ),

            "description":
            metadata.get(
                "description",
                metadata.get(
                    "reel_description",
                    ""
                )
            ),

            "hashtags":
            metadata.get(
                "hashtags",
                metadata.get(
                    "reel_hashtags",
                    []
                )
            ),

            "highlights":
            metadata.get(
                "all_highlights",
                metadata.get(
                    "highlights",
                    []
                )
            ),

            "stats":
            metadata.get(
                "stats",
                {}
            ),

            "final_reel":
            metadata.get(
                "final_reel",
                ""
            ),

            "vertical_reel":
            metadata.get(
                "vertical_reel",
                ""
            ),

            "thumbnail":
            metadata.get(
                "thumbnail",
                ""
            ),

            "result_json":
            str(
                output_file
            )

        }

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                export_data,
                file,
                indent=4
            )

        print(
            "RESULT JSON SAVED:",
            output_file
        )

        return str(
            output_file
        )