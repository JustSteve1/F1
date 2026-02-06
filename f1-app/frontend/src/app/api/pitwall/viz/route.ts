
import { NextResponse } from "next/server";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { graph, getSystemPrompt } from "@/app/pitwall/agent/graph";
import { logPrompt } from "@/lib/db/prompt_log";

export async function POST(req: Request) {
    try {
        const { prompt } = await req.json();

        if (!prompt) {
            return NextResponse.json(
                { error: "Missing required field: prompt" },
                { status: 400 }
            );
        }

        const inputs = {
            messages: [
                new SystemMessage({
                    content: getSystemPrompt()
                }),
                new HumanMessage({
                    content: `User Question: "${prompt}"`
                })
            ]
        };

        const config = { configurable: { thread_id: "1" }, recursionLimit: 50 };

        // Invoke graph
        const finalState: any = await graph.invoke(inputs, config);
        const lastMessage = finalState.messages[finalState.messages.length - 1];

        let responseText = lastMessage.content;
        console.log("Agent Response:", responseText);

        // 1. Write Thinking Process to File (as requested)
        const fs = await import('fs');
        const path = await import('path');

        try {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const sanitizedPrompt = prompt.substring(0, 20).replace(/[^a-z0-9]/gi, '_');
            const logDir = path.join(process.cwd(), 'logs');
            const logFile = path.join(logDir, `logic-${timestamp}-${sanitizedPrompt}.md`);

            if (!fs.existsSync(logDir)) {
                fs.mkdirSync(logDir, { recursive: true });
            }

            const logContent = `# User Prompt\n${prompt}\n\n# Agent Response\n${responseText}`;
            fs.writeFileSync(logFile, logContent);
            console.log(`Thinking process saved to: ${logFile}`);
        } catch (logErr) {
            console.error("Failed to write logic log:", logErr);
        }

        // Async Log (Fire & Forget) - Database
        const modelUsed = "gemini-3-flash-preview";
        logPrompt(prompt, responseText as string, modelUsed).catch(err => console.error("Log failed", err));

        // 2. Parse JSON (Robustly)
        let responseJson;
        try {
            if (typeof responseText === 'string') {
                // Find JSON block
                const jsonMatch = responseText.match(/\{[\s\S]*\}/);
                if (jsonMatch) {
                    responseJson = JSON.parse(jsonMatch[0]);
                } else {
                    throw new Error("No JSON found in response");
                }
            } else {
                throw new Error("Unexpected response format");
            }
        } catch (e) {
            console.error("JSON Parse Error:", e);
            // Fallback: If no JSON, treat entire text as explanation (if possible) or error
            return NextResponse.json({
                error: "Agent failed to produce valid JSON.",
                raw: responseText
            }, { status: 500 });
        }

        return NextResponse.json(responseJson);

    } catch (error: any) {
        console.error("Agent API Error:", error);
        return NextResponse.json(
            { error: error?.message || "Unknown error in agent workflow" },
            { status: 500 }
        );
    }
}
