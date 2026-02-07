
import { NextResponse } from "next/server";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { HumanMessage } from "@langchain/core/messages";

// Initialize model similarly to the main agent
// We use gemini-1.5-flash which is known to handle audio well for transcription
const model = new ChatGoogleGenerativeAI({
    model: "gemini-1.5-flash",
    apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY,
    temperature: 0,
});

export async function POST(req: Request) {
    try {
        const formData = await req.formData();
        const file = formData.get("audio") as File;

        if (!file) {
            return NextResponse.json({ error: "No audio file provided" }, { status: 400 });
        }

        const arrayBuffer = await file.arrayBuffer();
        const base64Audio = Buffer.from(arrayBuffer).toString("base64");

        // Construct Multimodal Message
        const message = new HumanMessage({
            content: [
                {
                    type: "text",
                    text: "Transcribe exactly what is said in this audio. Do not add any commentary, just the raw text."
                },
                {
                    type: "image_url", // LangChain uses image_url generic for media, but let's check media_type
                    image_url: {
                        url: `data:${file.type || "audio/webm"};base64,${base64Audio}`
                    }
                }
            ]
        });

        const response = await model.invoke([message]);
        const text = response.content;
        console.log("Transcription:", text);

        return NextResponse.json({ text });

    } catch (error: any) {
        console.error("Transcription Error:", error);
        return NextResponse.json(
            { error: error.message || "Failed to transcribe" },
            { status: 500 }
        );
    }
}
