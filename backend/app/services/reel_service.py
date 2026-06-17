import subprocess
from pathlib import Path


class ReelService:

    @staticmethod
    def merge_clips(
        clip_paths: list
    ):

        output_folder = Path(
            "storage/highlights"
        )

        output_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        list_file = (
            output_folder /
            "clips.txt"
        )

        with open(
            list_file,
            "w",
            encoding="utf-8"
        ) as file:

            print("\nMerging clips:")

            for clip in clip_paths:

                absolute_path = (
                    Path(clip)
                    .resolve()
                    .as_posix()
                )

                print(absolute_path)

                file.write(
                    f"file '{absolute_path}'\n"
                )

        final_video = (
            output_folder /
            "final_highlight_reel.mp4"
        )

        command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(final_video)
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            print(result.stderr)

            raise Exception(
                f"Merge failed: {result.stderr}"
            )

        return {
            "final_video":
            str(final_video)
        }