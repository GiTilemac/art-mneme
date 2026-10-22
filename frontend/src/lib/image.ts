import { MAX_PHOTO_BYTES, PHOTO_MAX_EDGE } from "./domain";

/** Shrinks any browser-readable image to ~2,500px longest edge and returns a JPEG. */
export async function prepareJpeg(file: File): Promise<Blob> {
  if (file.size > MAX_PHOTO_BYTES) throw new Error("This photo is larger than 30 MB.");
  let bmp: ImageBitmap;
  try {
    bmp = await createImageBitmap(file);
  } catch {
    throw new Error("This file type is not supported.");
  }
  const scale = Math.min(1, PHOTO_MAX_EDGE / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bmp.width * scale);
  canvas.height = Math.round(bmp.height * scale);
  canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  bmp.close();
  return new Promise((res, rej) =>
    canvas.toBlob((b) => (b ? res(b) : rej(new Error("Could not process photo."))), "image/jpeg", 0.88),
  );
}
