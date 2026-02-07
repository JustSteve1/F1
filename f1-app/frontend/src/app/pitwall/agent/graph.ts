
import { HumanMessage, AIMessage, BaseMessage } from "@langchain/core/messages";
import { StateGraph, END } from "@langchain/langgraph";
import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { ToolNode } from "@langchain/langgraph/prebuilt";
import { tools } from "./tools";

// Define the State
interface AgentState {
    messages: BaseMessage[];
}

import { loadSkill } from "@/lib/agent/skill_loader";

// Load configuration ONCE at startup (or per request if needed hot-reload)
const skill = loadSkill();

// 1. Initialize Model
const model = new ChatGoogleGenerativeAI({
    model: skill.model,
    apiKey: process.env.GOOGLE_GENERATIVE_AI_API_KEY,
    temperature: 0,
}).bindTools(tools);

export const getSystemPrompt = () => skill.instructions;

// 2. Define Nodes
const shouldContinue = (state: AgentState) => {
    const { messages } = state;
    const lastMessage = messages[messages.length - 1] as AIMessage;
    // If the LLM makes a tool call, verify we should go to "tools"
    if (lastMessage.tool_calls && lastMessage.tool_calls.length > 0) {
        return "tools";
    }
    return END;
};

const callModel = async (state: AgentState) => {
    const { messages } = state;

    // System Prompt injection if not present
    // Simplified for now, we can enhance later
    const response = await model.invoke(messages);
    return { messages: [response] };
};

const toolNode = new ToolNode(tools);

// 3. Define Graph
const workflow = new StateGraph<AgentState>({
    channels: { messages: { reducer: (a: BaseMessage[], b: BaseMessage[]) => a.concat(b), default: () => [] } }
})
    .addNode("agent", callModel)
    .addNode("tools", toolNode)
    .addEdge("__start__", "agent")
    .addConditionalEdges("agent", shouldContinue)
    .addEdge("tools", "agent");

// 4. Compile
export const graph = workflow.compile();
