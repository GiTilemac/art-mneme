import { useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { Button, type ButtonProps } from "@/components/ui/button";
import { prepareJpeg } from "@/lib/image";

/** Opens the file picker, shrinks the photo to JPEG, hands it back. */
export function PhotoButton({
  onPhoto,
  children,
  ...props
}: { onPhoto: (jpeg: Blob) => Promise<void> | void; children: ReactNode } & Omit<ButtonProps, "onClick">) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  return (
    <>
      <input
        ref={ref}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={async (e) => {
          const f = e.target.files?.[0];
          e.target.value = "";
          if (!f) return;
          setBusy(true);
          try {
            await onPhoto(await prepareJpeg(f));
          } catch (err) {
            toast.error((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      />
      <Button type="button" disabled={busy} onClick={() => ref.current?.click()} {...props}>
        {busy ? "Processing…" : children}
      </Button>
    </>
  );
}
