// Theme color constants
export const COLORS = {
  // Alignment colors
  TOWN: '#22c55e',      // Green
  MAFIA: '#ef4444',     // Red
  NEUTRAL: '#eab308',   // Yellow
  
  // UI colors
  BORDER_DEFAULT: '#334155',
  BORDER_HIGHLIGHT: '#22c55e',
  BORDER_BLUE: '#3b82f6',
  
  // Log event colors
  LOG_SYSTEM: '#94a3b8',
  LOG_KILL: '#ef4444',
  LOG_PROTECT: '#22c55e',
  LOG_INVESTIGATE: '#06b6d4',
  LOG_VOTE: '#f59e0b',
  LOG_ABILITY: '#8b5cf6',
  LOG_WIN: '#fbbf24',
  LOG_INFO: '#64748b',
  
  // Dividers
  DIVIDER: '#475569',
  
  // Backgrounds
  BG_DARK_PRIMARY: '#0f172a',
  BG_DARK_SECONDARY: '#1e293b',
  
  // Error/Warning
  ERROR: '#dc3545',
} as const;

export const getAlignmentColor = (alignment: 'TOWN' | 'MAFIA' | 'NEUTRAL'): string => {
  return COLORS[alignment];
};

export const getLogEventColor = (eventType: string): string => {
  const typeMap: Record<string, string> = {
    system: COLORS.LOG_SYSTEM,
    kill: COLORS.LOG_KILL,
    protect: COLORS.LOG_PROTECT,
    investigate: COLORS.LOG_INVESTIGATE,
    vote: COLORS.LOG_VOTE,
    ability: COLORS.LOG_ABILITY,
    win: COLORS.LOG_WIN,
  };
  return typeMap[eventType] || COLORS.LOG_INFO;
};
