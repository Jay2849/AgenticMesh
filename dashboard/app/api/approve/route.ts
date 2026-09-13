import { NextResponse } from "next/server";
import Redis from "ioredis";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const redisUrl = process.env.UPSTASH_REDIS_URL || "redis://redis:6379/0";
    const redis = new Redis(redisUrl);

    await redis.publish("approvals", JSON.stringify(body));
    redis.disconnect();

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to publish approval", error);
    return NextResponse.json({ success: false, error: "Internal Server Error" }, { status: 500 });
  }
}
