
import { NextResponse } from "next/server";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { loadSkill } from "@/lib/agent/skill_loader";
import path from 'path';

// Load the Factory Skill
// We pass the relative path because loadSkill appends it to process.cwd()
const FACTORY_SKILL_REL_PATH = 'src/app/factory/skills/SKILL.md';

export async function POST(req: Request) {
    try {
        const formData = await req.formData();
        const file = formData.get("video") as File;
        const prompt = formData.get("prompt") as string || "Analyze this video.";

        if (!file) {
            return NextResponse.json({ error: "No video file provided" }, { status: 400 });
        }

        console.log(`🎥 Received video: ${file.name} (${file.size} bytes)`);

        // Reload skill on every request to allow hot-editing
        const { loadSkill } = await import("@/lib/agent/skill_loader");
        const skill = loadSkill(FACTORY_SKILL_REL_PATH);

        // Initialize Gemini 3 (or whatever is set in SKILL.md)
        // We set maxOutputTokens to allow for long analyses
        const model = new ChatGoogleGenerativeAI({
            model: skill.model, // Should be 'gemini-2.0-flash-exp'
            apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY,
            temperature: 0.2,
            maxOutputTokens: 2048,
        });

        const arrayBuffer = await file.arrayBuffer();
        const base64Video = Buffer.from(arrayBuffer).toString("base64");

        const messages = [
            new SystemMessage(skill.instructions),
            new HumanMessage({
                content: [
                    { type: "text", text: prompt },
                    {
                        type: "image_url", // LangChain generic media type
                        image_url: {
                            url: `data:${file.type};base64,${base64Video}`
                        }
                    }
                ]
            })
        ];

        // Streaming Response for "Log" effect on UI
        // We will return a stream so the UI can show the "thinking" process
        const stream = await model.stream(messages);

        // Next.js Streaming Response
        const encoder = new TextEncoder();

        return new NextResponse(
            new ReadableStream({
                async start(controller) {
                    try {
                        for await (const chunk of stream) {
                            const text = chunk.content;
                            if (text) {
                                controller.enqueue(encoder.encode(text as string));
                            }
                        }
                        controller.close();
                    } catch (err) {
                        console.error("Streaming error:", err);
                        controller.error(err);
                    }
                },
            }),
            {
                headers: {
                    "Content-Type": "text/plain; charset=utf-8",
                },
            }
        );

    } catch (error: any) {
        console.error("Factory Analysis Error:", error);
        return NextResponse.json(
            { error: error.message || "Failed to analyze video" },
            { status: 500 }
        );
    }
}
