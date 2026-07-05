const FRIENDLY_UPLOAD_ERRORS: Array<{ match: RegExp; message: string }> = [
  {
    match: /unable to reach the server|network|failed to fetch/i,
    message: "Upload interrupted.\nPlease check your connection and try again.",
  },
  {
    match: /exceeds.*(size|mb)|too large/i,
    message: "This file exceeds the supported upload size.",
  },
  {
    match: /unsupported|not allowed|file type not supported|invalid extension/i,
    message: "Please upload an MP4, MOV, AVI or MKV file.",
  },
];

export function getFriendlyUploadErrorMessage(rawMessage: string): string {
  const match = FRIENDLY_UPLOAD_ERRORS.find((entry) => entry.match.test(rawMessage));
  return match ? match.message : rawMessage;
}
