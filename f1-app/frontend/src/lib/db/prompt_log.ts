import { prisma } from "@/lib/prisma";

export async function logPrompt(
    prompt: string,
    response: string,
    model: string,
    toolCalls?: any
) {
    try {
        await prisma.promptLog.create({
            data: {
                prompt,
                response,
                model,
                toolCalls: toolCalls ? JSON.stringify(toolCalls) : undefined
            }
        });
        console.log("Prompt logged to DB.");
    } catch (error) {
        console.error("Failed to log prompt:", error);
        // Don't throw, just log error so we don't break the user request
    }
}
