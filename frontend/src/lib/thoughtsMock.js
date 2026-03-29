export const initialThoughts = [
    {
        id: 1,
        title: "Project Ideas",
        content: "Build a fluid application with Framer Motion and shadcn/ui. Prioritize dark mode and glassy animations.",
        user_id: 1,
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString()
    },
    {
        id: 2,
        title: "Grocery list",
        content: "Almond milk, eggs, whole wheat bread, avocados, Greek yogurt.",
        user_id: 1,
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString()
    },
    {
        id: 3,
        title: "Meeting notes - March 24",
        content: "Discuss API structure for the Journal and Thoughts modules. Make sure the models cleanly separate user spaces.",
        user_id: 1,
        created_at: new Date().toISOString()
    }
];

export function cloneInitialThoughts() {
    return [...initialThoughts];
}
