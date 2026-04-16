// Shared types for Game Creator workflow

export interface RoleSlot {
  roleId: number;
  roleName: string;
  count: number;
}

export interface Phase {
  name: string;
  phase_type: 'NIGHT' | 'DAY' | 'VOTING';
  order: number;
}

export interface Criterion {
  type: 'ROLE_COUNT' | 'ALIGNMENT_COUNT' | 'SURVIVAL';
  target: string;
  count: number;
}

export interface WinCondition {
  name: string;
  winner_alignment: number;
  criteria: Criterion[];
  order: number;
}

export interface GameData {
  name: string;
  min_players: number;
  max_players: number;
  role_slots: RoleSlot[];
  phases: Phase[];
  win_conditions: WinCondition[];
}
