import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/services";
import hero from "@/assets/hero-gallery.jpg";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ArtMneme — remember the art you've seen" },
      { name: "description", content: "Collect artworks you've encountered, keep notes and detail photos, and explore how they connect." },
      { property: "og:title", content: "ArtMneme — remember the art you've seen" },
      { property: "og:description", content: "A personal artwork collection and relationship explorer." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});

function Landing() {
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    api.me().then((u) => setSignedIn(!!u));
  }, []);
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col justify-between p-8 sm:p-14">
        <span className="font-display text-2xl">ArtMneme</span>
        <div className="max-w-md py-16">
          <p className="eyebrow">A personal collection</p>
          <h1 className="mt-4 text-5xl leading-[1.05] sm:text-6xl">Remember every artwork that stopped you.</h1>
          <p className="mt-6 text-muted-foreground">
            Keep the paintings you've stood in front of, the ones you still hope to see, and discover how they relate.
          </p>
          <div className="mt-10 flex gap-3">
            {signedIn ? (
              <Button asChild size="lg"><Link to="/collection">Open my collection</Link></Button>
            ) : (
              <>
                <Button asChild size="lg"><Link to="/auth" search={{ mode: "signup" }}>Start collecting</Link></Button>
                <Button asChild size="lg" variant="ghost"><Link to="/auth">Sign in</Link></Button>
              </>
            )}
          </div>
        </div>
        <p className="eyebrow">Collection · Watchlist · Relationships</p>
      </div>
      <img src={hero} alt="A painting in a quiet gallery" width={1600} height={1008} className="hidden h-full w-full object-cover lg:block" />
    </div>
  );
}
