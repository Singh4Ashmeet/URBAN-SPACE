import { NextResponse, type NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const TILE_HOSTS = ["a", "b", "c"];

type TileParams = {
  z: string;
  x: string;
  y: string;
};

export async function GET(_request: NextRequest, context: { params: Promise<TileParams> }) {
  const { z, x, y } = await context.params;
  const yValue = y.endsWith(".png") ? y.slice(0, -4) : y;

  if (!isTilePart(z) || !isTilePart(x) || !isTilePart(yValue)) {
    return NextResponse.json({ error: "Invalid tile coordinates" }, { status: 400 });
  }

  const host = TILE_HOSTS[(Number(x) + Number(yValue)) % TILE_HOSTS.length];
  const upstreamUrl = `https://${host}.basemaps.cartocdn.com/rastertiles/voyager/${z}/${x}/${yValue}.png`;
  const upstream = await fetch(upstreamUrl, {
    headers: {
      "User-Agent": "UrbanShield local development map proxy"
    },
    next: { revalidate: 60 * 60 * 24 }
  });

  if (!upstream.ok || !upstream.body) {
    return NextResponse.json({ error: "Map tile unavailable" }, { status: 502 });
  }

  return new NextResponse(upstream.body, {
    headers: {
      "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
      "Content-Type": upstream.headers.get("Content-Type") ?? "image/png"
    },
    status: 200
  });
}

function isTilePart(value: string) {
  return /^\d+$/.test(value);
}
