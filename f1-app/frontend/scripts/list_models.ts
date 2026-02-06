
import { GoogleGenerativeAI } from "@google/generative-ai";
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const apiKey = process.env.GOOGLE_GENERATIVE_AI_API_KEY;
if (!apiKey) {
    console.error("No API Key found in .env.local");
    process.exit(1);
}

const genAI = new GoogleGenerativeAI(apiKey);

async function listModels() {
    try {
        // This is a bit of a hack as the Node SDK maps listModels differently, 
        // relying on the REST API structure or specific methods. 
        // Actually, the SDK *does* have a getGenerativeModel but listing might need direct fetch 
        // or using the model manager if exposed.

        // Let's try a direct fetch to the API endpoint to be sure, 
        // or check if we can brute force check a few common names if listing isn't easy.

        // Better: Use the raw API to list models
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`);
        if (!response.ok) {
            throw new Error(`Failed to list models: ${response.status} ${await response.text()}`);
        }

        const data = await response.json();
        const models = data.models || [];

        console.log("Available Models:");
        models.forEach((m: any) => {
            if (m.name.includes("gemini")) {
                console.log(`- ${m.name} (${m.supportedGenerationMethods?.join(', ')})`);
            }
        });

    } catch (error) {
        console.error("Error listing models:", error);
    }
}

listModels();
