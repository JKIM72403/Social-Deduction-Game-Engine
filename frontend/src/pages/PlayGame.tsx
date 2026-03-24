import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API } from "../services/api";
import {
    Box, Typography, Card, CardContent, Button, FormControl, Select, MenuItem,
    Paper, List, ListItem, ListItemText, CircularProgress, Divider, Alert, Snackbar
} from "@mui/material";

type Player = {
    name: string;
    is_alive: boolean;
    role: string;
    alignment: string;
};

type Ability = {
    index: number;
    name: string;
    phase: string;
};

type GameState = {
    session_id: string;
    phase: string;
    turn: number;
    players: Player[];
    me: {
        name: string;
        is_alive: boolean;
        role: string;
        alignment: string;
        abilities: Ability[];
    };
    logs: string[];
};

function getPhaseGuidance(gameState: GameState) {
    if (gameState.phase === "GAME_OVER") {
        return {
            title: "Game finished",
            message: "Review the final logs and return to the catalog or restart with another template.",
            severity: "success" as const,
        };
    }

    if (!gameState.me.is_alive) {
        return {
            title: "You are eliminated",
            message: "You can still follow the logs and player list while the remaining players finish the game.",
            severity: "info" as const,
        };
    }

    if (gameState.phase === "NIGHT") {
        const nightAbilities = gameState.me.abilities.filter(ab => ab.phase === "NIGHT");
        return nightAbilities.length > 0
            ? {
                title: "Night phase",
                message: "Choose one of your abilities and select a living target, then submit your action.",
                severity: "info" as const,
            }
            : {
                title: "Night phase",
                message: "You do not have a night ability. Submit to skip and let the night resolve.",
                severity: "info" as const,
            };
    }

    if (gameState.phase === "VOTING") {
        return {
            title: "Voting phase",
            message: "Select one living player to vote for elimination this turn.",
            severity: "warning" as const,
        };
    }

    if (gameState.phase === "DAY") {
        return {
            title: "Day phase",
            message: "Review the latest events, discuss, and end the day when you are ready to proceed.",
            severity: "info" as const,
        };
    }

    return {
        title: `Phase: ${gameState.phase}`,
        message: "Follow the on-screen action panel for the next available move.",
        severity: "info" as const,
    };
}

export default function PlayGame() {
    const { id: templateId } = useParams();
    const navigate = useNavigate();
    const [gameState, setGameState] = useState<GameState | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);

    // Form states
    const [selectedAbility, setSelectedAbility] = useState<number>(-1);
    const [selectedAbilityTarget, setSelectedAbilityTarget] = useState<string>("");
    const [selectedVoteTarget, setSelectedVoteTarget] = useState<string>("");
    
    // Voting phase flow
    const [votingSubPhase, setVotingSubPhase] = useState<'ABILITY' | 'VOTE'>('ABILITY');
    const [hasUsedAbilityThisPhase, setHasUsedAbilityThisPhase] = useState(false);

    const currentAbilities = gameState?.me.abilities.filter(ab => ab.phase === gameState.phase) || [];

    useEffect(() => {
        // Start the game session
        API.post("/game-sessions/", { template_id: templateId, user_name: "You" })
            .then((res) => {
                setGameState(res.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to start game session", err);
                setError(err.response?.data?.error || "Failed to start game session.");
                setLoading(false);
            });
    }, [templateId]);

    useEffect(() => {
        if (currentAbilities.length > 0 && !hasUsedAbilityThisPhase) {
            setSelectedAbility(currentAbilities[0].index);
            setVotingSubPhase('ABILITY');
        } else {
            setSelectedAbility(-1);
            setVotingSubPhase('VOTE');
        }
        
        // Reset ability usage flag on phase change
        if (gameState?.phase !== "VOTING") {
            setHasUsedAbilityThisPhase(false);
        }
    }, [gameState?.phase, currentAbilities.length, hasUsedAbilityThisPhase]);

    const handleAction = async (actionData: any) => {
        if (!gameState || isSubmitting) return;

        setIsSubmitting(true);
        setActionError(null);

        try {
            const res = await API.post(`/game-sessions/${gameState.session_id}/act/`, {
                user_name: "You",
                action: actionData
            });
            setGameState(res.data);
        } catch (err: any) {
            console.error("Action failed", err);
            setActionError(err?.response?.data?.error || "Action failed. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    };

    const submitNightAction = (e: React.FormEvent) => {
        e.preventDefault();
        const currentAbilities = gameState?.me.abilities.filter(ab => ab.phase === gameState.phase) || [];
        if (currentAbilities.length === 0) {
            void handleAction(null); // Just skip
            return;
        }
        void handleAction({
            ability_index: selectedAbility,
            target: selectedAbilityTarget
        });
    };

    const submitVoteAction = (e: React.FormEvent) => {
        e.preventDefault();
        void handleAction({
            action: "vote",
            target: selectedVoteTarget
        });
    };

    if (loading) return (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
        </Box>
    );

    if (error) return (
        <Box sx={{ mt: 4 }}>
            <Alert severity="error">{error}</Alert>
        </Box>
    );

    if (!gameState) return (
        <Box sx={{ mt: 4 }}>
            <Alert severity="warning">Game state not found.</Alert>
        </Box>
    );

    const phaseGuidance = getPhaseGuidance(gameState);
    const alivePlayers = gameState.players.filter((p) => p.is_alive);
    const eliminatedPlayers = gameState.players.filter((p) => !p.is_alive);

    return (
        <Box sx={{ maxWidth: 900, mx: 'auto', mt: 4, display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Paper sx={{ p: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                    <Typography variant="h5" fontWeight={600}>
                        Phase: {gameState.phase}
                    </Typography>
                    <Typography variant="subtitle1" color="text.secondary">
                        Turn {gameState.turn}
                    </Typography>
                </Box>
                <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="body1" fontWeight={600}>
                        {gameState.me.name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        {gameState.me.role} ({gameState.me.alignment})
                    </Typography>
                    <Typography variant="body2" color={gameState.me.is_alive ? 'success.main' : 'error.main'} fontWeight={600}>
                        {gameState.me.is_alive ? "Alive" : "Dead"}
                    </Typography>
                </Box>
            </Paper>

            <Alert severity={phaseGuidance.severity}>
                <Typography variant="subtitle2">{phaseGuidance.title}</Typography>
                <Typography variant="body2">{phaseGuidance.message}</Typography>
            </Alert>

            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '2fr 1fr' }, gap: 3 }}>
                <Card sx={{ height: 400, display: 'flex', flexDirection: 'column' }}>
                    <CardContent sx={{ flexGrow: 1, overflowY: 'auto' }}>
                        <Typography variant="h6" gutterBottom>Game Logs</Typography>
                        <Divider sx={{ mb: 2 }} />
                        <List disablePadding>
                            {gameState.logs.map((log, index) => (
                                <ListItem key={index} disablePadding sx={{ mb: 1 }}>
                                    <ListItemText primary={log} primaryTypographyProps={{ variant: 'body2' }} />
                                </ListItem>
                            ))}
                        </List>
                    </CardContent>
                </Card>

                <Card sx={{ height: 400, display: 'flex', flexDirection: 'column' }}>
                    <CardContent sx={{ flexGrow: 1, overflowY: 'auto' }}>
                        <Typography variant="h6" gutterBottom>Players</Typography>
                        <Divider sx={{ mb: 2 }} />
                        <Typography variant="subtitle2" color="success.main" sx={{ mb: 1 }}>
                            Alive ({alivePlayers.length})
                        </Typography>
                        <List disablePadding sx={{ mb: eliminatedPlayers.length > 0 ? 2 : 0 }}>
                            {alivePlayers.map(p => (
                                <ListItem key={p.name} disablePadding sx={{ mb: 1 }}>
                                    <ListItemText
                                        primary={p.name === gameState.me.name ? `${p.name} (You)` : p.name}
                                        primaryTypographyProps={{
                                            fontWeight: p.name === gameState.me.name ? 700 : 400,
                                            color: p.name === gameState.me.name ? 'primary.main' : 'text.primary'
                                        }}
                                    />
                                </ListItem>
                            ))}
                        </List>

                        {eliminatedPlayers.length > 0 && (
                            <>
                                <Typography variant="subtitle2" color="error.main" sx={{ mb: 1 }}>
                                    Eliminated ({eliminatedPlayers.length})
                                </Typography>
                                <List disablePadding>
                                    {eliminatedPlayers.map(p => (
                                        <ListItem key={p.name} disablePadding sx={{ mb: 1 }}>
                                            <ListItemText
                                                primary={p.name === gameState.me.name ? `${p.name} (You)` : p.name}
                                                secondary={p.role}
                                                sx={{
                                                    textDecoration: 'line-through',
                                                    color: 'text.disabled'
                                                }}
                                                primaryTypographyProps={{
                                                    fontWeight: p.name === gameState.me.name ? 700 : 400
                                                }}
                                                secondaryTypographyProps={{ color: 'error.main' }}
                                            />
                                        </ListItem>
                                    ))}
                                </List>
                            </>
                        )}
                    </CardContent>
                </Card>
            </Box>

            {gameState.phase !== "GAME_OVER" ? (
                <Paper sx={{ p: 3, bgcolor: 'background.paper' }}>
                    <Typography variant="h6" gutterBottom>Take Action</Typography>
                    <Divider sx={{ mb: 2 }} />
                    
                    {!gameState.me.is_alive ? (
                        <Typography color="text.secondary">You are dead. Wait for the game to finish.</Typography>
                    ) : (
                        <Box>
                            {gameState.phase === "NIGHT" && (
                                <form onSubmit={submitNightAction}>
                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                        {gameState.me.abilities.length > 0
                                            ? "Night actions happen in secret. Pick an ability and target."
                                            : "You have no night actions this turn. Submit to continue."}
                                    </Typography>
                                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                                        {currentAbilities.length > 0 ? (
                                            <>
                                                <FormControl size="small" sx={{ minWidth: 150 }}>
                                                    <Select
                                                        value={selectedAbility}
                                                        onChange={e => setSelectedAbility(Number(e.target.value))}
                                                        disabled={isSubmitting}
                                                    >
                                                        {currentAbilities.map(ab => (
                                                            <MenuItem key={ab.index} value={ab.index}>{ab.name}</MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                                
                                                <FormControl size="small" sx={{ minWidth: 150 }}>
                                                    <Select
                                                        value={selectedAbilityTarget}
                                                        onChange={e => setSelectedAbilityTarget(e.target.value)}
                                                        displayEmpty
                                                        required
                                                        disabled={isSubmitting}
                                                    >
                                                        <MenuItem value="" disabled>Select Target</MenuItem>
                                                        {gameState.players.filter(p => p.is_alive).map(p => (
                                                            <MenuItem key={p.name} value={p.name}>{p.name}</MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                                <Button type="submit" variant="contained" color="success" disabled={isSubmitting}>
                                                    {isSubmitting ? "Submitting..." : "Use Ability"}
                                                </Button>
                                            </>
                                        ) : (
                                            <>
                                                <Typography>No abilities to use tonight.</Typography>
                                                <Button type="submit" variant="contained" color="inherit" disabled={isSubmitting}>
                                                    {isSubmitting ? "Submitting..." : "Sleep"}
                                                </Button>
                                            </>
                                        )}
                                    </Box>
                                </form>
                            )}

                            {gameState.phase === "VOTING" && (
                                <Box>
                                    {votingSubPhase === 'ABILITY' && currentAbilities.length > 0 ? (
                                        <Box sx={{ mb: 3, p: 3, border: '1px dashed grey', borderRadius: 2, bgcolor: 'rgba(25, 118, 210, 0.04)' }}>
                                            <Typography variant="h6" gutterBottom color="primary">Phase 1: Vote Manipulation</Typography>
                                            <Typography variant="body2" sx={{ mb: 3 }} color="text.secondary">
                                                Select an ability to use before final voting begins. You can only use one ability per voting round.
                                            </Typography>
                                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                                                <FormControl size="small" sx={{ minWidth: 150 }}>
                                                    <Select
                                                        value={selectedAbility}
                                                        onChange={e => setSelectedAbility(Number(e.target.value))}
                                                        disabled={isSubmitting}
                                                    >
                                                        {currentAbilities.map(ab => (
                                                            <MenuItem key={ab.index} value={ab.index}>{ab.name}</MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                                <FormControl size="small" sx={{ minWidth: 150 }}>
                                                    <Select
                                                        value={selectedAbilityTarget}
                                                        onChange={e => setSelectedAbilityTarget(e.target.value)}
                                                        displayEmpty
                                                        disabled={isSubmitting}
                                                    >
                                                        <MenuItem value="" disabled>Select Target</MenuItem>
                                                        {gameState.players.filter(p => p.is_alive).map(p => (
                                                            <MenuItem key={p.name} value={p.name}>{p.name}</MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                                <Button 
                                                    onClick={async () => {
                                                        await handleAction({ ability_index: selectedAbility, target: selectedAbilityTarget });
                                                        setHasUsedAbilityThisPhase(true);
                                                        setVotingSubPhase('VOTE');
                                                    }} 
                                                    variant="contained" 
                                                    color="primary" 
                                                    disabled={isSubmitting || !selectedAbilityTarget}
                                                >
                                                    Use Ability
                                                </Button>
                                                <Button 
                                                    onClick={() => setVotingSubPhase('VOTE')} 
                                                    variant="text" 
                                                    disabled={isSubmitting}
                                                >
                                                    Skip to Vote
                                                </Button>
                                            </Box>
                                        </Box>
                                    ) : (
                                        <form onSubmit={submitVoteAction}>
                                            <Typography variant="h6" gutterBottom color="error">Phase 2: Final Vote</Typography>
                                            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                                                Manipulation phase is over. Cast your final vote for elimination.
                                            </Typography>
                                            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                                                <FormControl size="small" sx={{ minWidth: 150 }}>
                                                    <Select
                                                        value={selectedVoteTarget}
                                                        onChange={e => setSelectedVoteTarget(e.target.value)}
                                                        displayEmpty
                                                        required
                                                        disabled={isSubmitting}
                                                    >
                                                        <MenuItem value="" disabled>Select Target</MenuItem>
                                                        {gameState.players.filter(p => p.is_alive).map(p => (
                                                            <MenuItem key={p.name} value={p.name}>{p.name}</MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                                <Button type="submit" variant="contained" color="error" disabled={isSubmitting}>
                                                    {isSubmitting ? "Submit Vote" : "Confirm Vote"}
                                                </Button>
                                            </Box>
                                        </form>
                                    )}
                                </Box>
                            )}

                            {gameState.phase === "DAY" && (
                                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                    <Typography>Read the logs and player list, then end the day to move to voting.</Typography>
                                    <Button onClick={() => void handleAction(null)} variant="contained" color="warning" disabled={isSubmitting}>
                                        {isSubmitting ? "Submitting..." : "End Day"}
                                    </Button>
                                </Box>
                            )}
                        </Box>
                    )}
                </Paper>
            ) : (
                <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'success.light', color: 'success.contrastText' }}>
                    <Typography variant="h4" gutterBottom>Game Over!</Typography>
                    <Button 
                        variant="contained" 
                        color="primary" 
                        onClick={() => navigate("/")}
                        sx={{ mt: 2 }}
                    >
                        Back to Catalog
                    </Button>
                </Paper>
            )}

            <Snackbar
                open={Boolean(actionError)}
                autoHideDuration={5000}
                onClose={() => setActionError(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={() => setActionError(null)} severity="error" sx={{ width: '100%' }}>
                    {actionError}
                </Alert>
            </Snackbar>
        </Box>
    );
}
