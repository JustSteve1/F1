
import { GoogleGenerativeAI } from "@google/generative-ai";
import dotenv from 'dotenv';
import fs from 'fs';
dotenv.config({ path: '.env.local' });

const API_KEY = process.env.GOOGLE_GENERATIVE_AI_API_KEY;

if (!API_KEY) {
    console.error("❌ NO API KEY FOUND in .env.local");
    process.exit(1);
}

const genAI = new GoogleGenerativeAI(API_KEY);

async function test() {
    try {
        console.log("Fetching available models...");
        // Not all SDK versions support listModels directly via the main class, 
        // but let's try a direct request if the SDK allows, or just try a different known model.
        // Actually, let's try 'gemini-2.0-flash-exp' which is the latest preview, 
        // or 'gemini-1.5-flash-001' which is the stable version.

        const modelsToTry = ["gemini-1.5-flash-latest", "gemini-1.5-flash-001", "gemini-2.0-flash-exp", "gemini-pro"];

        for (const modelName of modelsToTry) {
            console.log(`Testing: ${modelName}`);
            try {
                const model = genAI.getGenerativeModel({ model: modelName });
                const result = await model.generateContent("Hello");
                console.log(`✅ SUCCESS: ${modelName}`);
                return; // Found one!
            } catch (e: any) {
                console.log(`❌ FAILED: ${modelName} - ${e.message.split(':')[0]}`);
            }
        }
    } catch (e: any) {
        console.error("❌ Test Failed:", e.message);
    }
}

test();
