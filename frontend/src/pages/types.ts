// Shared types for Game Creator workflow

export interface RoleSlot {
  roleId: number;
  roleName: string;
  count: number;
}

export interface GameData {
  name: string;
  min_players: number;
  max_players: number;
  role_slots: RoleSlot[];
}
