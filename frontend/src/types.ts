export type Alignment = {
    id: number;
    name: string;
    is_default: boolean;
    game_template?: number | null;
};

export type RoleSlot = {
    roleId: number;
    roleName: string;
    count: number;
    isDefault?: boolean;
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
    winner_alignment: number; // ID of the alignment
    winner_alignment_name?: string;
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
    is_default?: boolean;
};

export type RoleTemplate = {
    id: number;
    name: string;
    alignment: number; // ID of the alignment
    alignment_name?: string;
    description: string;
    ability_details: AbilityTemplate[];
    is_default?: boolean;
    game_template?: number | null;
};

export type SessionSummary = {
    id: number;
    join_code: string;
    status: "LOBBY" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";
    current_phase: "WAITING" | "DAY" | "VOTING" | "NIGHT" | "GAME_OVER";
    turn_number: number;
    template_id: number;
    template_name: string;
    host_user_id: number | null;
    host_username: string | null;
    participant_count: number;
    ready_count: number;
    all_ready: boolean;
    created_at: string;
    updated_at: string;
    started_at: string | null;
    ended_at: string | null;
};

export type SessionParticipant = {
    id: number;
    user_id: number;
    username: string;
    display_name: string;
    seat_order: number;
    is_ready: boolean;
    is_connected: boolean;
    is_alive: boolean;
    role_name: string;
    role_alignment: string;
    joined_at: string;
    last_seen_at: string;
    eliminated_at: string | null;
};

export type SessionState = {
    mode?: string;
    phase?: string;
    turn_number?: number;
    winner?: string | null;
    phase_index?: number;
    phase_order?: Array<{ name: string; type: string }>;
    events?: string[];
    players?: Array<{
        participant_id: number;
        display_name: string;
        is_alive: boolean;
        role_name?: string;
        role_alignment?: string;
    }>;
    logs?: Array<{
        type: string;
        message: string;
        turn: number;
        visible_to: "all" | string[];
    }>;
    action_state?: {
        status?: "OPEN" | "CLOSED";
        required_participant_ids?: number[];
        submitted_participant_ids?: number[];
        submitted_count?: number;
        actions_needed?: number;
    };
    vote_state?: {
        status?: "OPEN" | "RESOLVED";
        required_participant_ids?: number[];
        submitted_participant_ids?: number[];
        submitted_count?: number;
        votes_needed?: number;
        last_result?: {
            turn_number: number;
            resolved_at: string;
            eliminated_participant_id: number | null;
            eliminated_display_name: string;
            majority_threshold: number;
            outcome_message: string;
            vote_counts: Array<{
                target_participant_id: number;
                target_display_name: string;
                count: number;
            }>;
        } | null;
    };
};

export type SessionAbility = {
    index: number;
    name: string;
    phase: "NIGHT" | "DAY" | "VOTING" | string;
    ability_type: string;
    target_self?: boolean;
};

export type SessionViewer = {
    participant_id: number;
    display_name: string;
    is_alive: boolean;
    role_name: string;
    role_alignment: string;
    abilities: SessionAbility[];
    phase_abilities: SessionAbility[];
    has_submitted_action: boolean;
    has_submitted_ability: boolean;
    has_submitted_vote: boolean;
    current_ability_target_id: number | null;
    current_vote_target_id: number | null;
    available_ability_target_ids: number[];
    available_vote_target_ids: number[];
    action_required: boolean;
};

export type SessionSnapshot = {
    session: SessionSummary;
    participants: SessionParticipant[];
    me: SessionViewer | null;
    state: SessionState;
};

export type SessionSocketMessage =
    | {
        type: "session.snapshot";
        reason: string;
        snapshot: SessionSnapshot;
    }
    | {
        type: "pong";
    }
    | {
        type: "error";
        message: string;
    };
