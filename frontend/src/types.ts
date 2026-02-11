export type RoleSlot = {
    roleId: number;
    roleName: string;
    count: number;
};

export type GameData = {
    name: string;
    min_players: number;
    max_players: number;
    role_slots: RoleSlot[];
};

export type AbilityTemplate = {
    id: number;
    name: string;
    ability_type: string;
    phase: string;
    description: string;
};
