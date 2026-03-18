export type RoleSlot = {
    roleId: number;
    roleName: string;
    count: number;
};

export type Phase = {
    id?: number;
    name: string;
    phase_type: 'NIGHT' | 'DAY' | 'VOTING';
    order: number;
};

export type Criterion = {
    type: 'ROLE_COUNT' | 'ALIGNMENT_COUNT' | 'SURVIVAL';
    target: string;
    count: number;
};

export type WinCondition = {
    id?: number;
    name: string;
    winner_alignment: 'TOWN' | 'MAFIA' | 'NEUTRAL';
    criteria: Criterion[];
    order: number;
};

export type GameData = {
    id?: number;
    name: string;
    min_players: number;
    max_players: number;
    is_public: boolean;
    role_slots: RoleSlot[];
    phases: Phase[];
    win_conditions: WinCondition[];
};

export type AbilityTemplate = {
    id: number;
    name: string;
    ability_type: string;
    phase: string;
    description: string;
};
