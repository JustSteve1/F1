import fs from 'fs';
import path from 'path';
import matter from 'gray-matter';

type SkillDefinition = {
    name: string;
    description: string;
    model: string;
    instructions: string;
};

export function loadSkill(skillPath: string = 'src/app/pitwall/skills/SKILL.md'): SkillDefinition {
    const fullPath = path.join(process.cwd(), skillPath);

    if (!fs.existsSync(fullPath)) {
        throw new Error(`Skill file not found at: ${fullPath}`);
    }

    const fileContent = fs.readFileSync(fullPath, 'utf8');
    const { data, content } = matter(fileContent);

    return {
        name: data.name || 'Unnamed Skill',
        description: data.description || '',
        model: data.model || 'gemini-2.0-flash', // Default fallback
        instructions: content.trim()
    };
}
