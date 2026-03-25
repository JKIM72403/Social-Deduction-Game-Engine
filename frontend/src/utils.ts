export function formatLogMessage(message: string, myName: string | undefined | null): string {
    if (!myName) return message;

    if (myName.toLowerCase() === 'you') {
        // Special case for single-player bots where myName is literally "You"
        return message
            .replace(/\bYou was\b/gi, "You were")
            .replace(/\bYou is\b/gi, "You are");
    }

    try {
        const escapedName = myName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const wasRegex = new RegExp(`(^|\\W)${escapedName} was\\b`, 'gi');
        const isRegex = new RegExp(`(^|\\W)${escapedName} is\\b`, 'gi');
        const possRegex = new RegExp(`(^|\\W)${escapedName}'s\\b`, 'gi');
        const nameRegex = new RegExp(`(^|\\W)${escapedName}(?!\\w)`, 'gi');

        return message
            .replace(wasRegex, "$1You were")
            .replace(isRegex, "$1You are")
            .replace(possRegex, "$1Your")
            .replace(nameRegex, "$1You");
    } catch {
        return message;
    }
}
