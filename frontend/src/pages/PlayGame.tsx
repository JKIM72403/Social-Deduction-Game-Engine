import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API } from "../services/api";
import {
    Box, Typography, Card, CardContent, Button, FormControl, Select, MenuItem,
    Paper, List, ListItem, ListItemText, CircularProgress, Divider, Alert, Snackbar,
    Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions
} from "@mui/material";
import {
    WarningAmberRounded as KillIcon,
    ShieldOutlined as ProtectIcon,
    SearchRounded as InvestigateIcon,
    HowToVoteRounded as VoteIcon,
    FlashOnRounded as AbilityIcon,
    EmojiEventsRounded as WinIcon,
    InfoOutlined as SystemIcon
} from '@mui/icons-material';
import { formatLogMessage } from "../utils";
import bgImage from '../assets/mafia_bg.png';

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

type LogEvent = {
    type: "phase_change" | "kill" | "protect" | "investigate" | "vote" | "ability" | "system" | "win";
    message: string;
    turn: number;
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
    logs: LogEvent[];
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

type LogStyleProps = {
    color: string;
    bgcolor: string;
    borderColor: string;
    icon: React.ElementType;
    fontWeight: number;
};

function getLogStyle(type: LogEvent["type"]): LogStyleProps {
    switch (type) {
        case "kill":
            return { color: '#fca5a5', bgcolor: 'rgba(239, 68, 68, 0.15)', borderColor: 'rgba(239, 68, 68, 0.6)', icon: KillIcon, fontWeight: 700 };
        case "protect":
            return { color: '#86efac', bgcolor: 'rgba(34, 197, 94, 0.15)', borderColor: 'rgba(34, 197, 94, 0.6)', icon: ProtectIcon, fontWeight: 500 };
        case "investigate":
            return { color: '#93c5fd', bgcolor: 'rgba(56, 130, 246, 0.15)', borderColor: 'rgba(56, 130, 246, 0.6)', icon: InvestigateIcon, fontWeight: 500 };
        case "vote":
            return { color: '#fdba74', bgcolor: 'rgba(249, 115, 22, 0.1)', borderColor: 'rgba(249, 115, 22, 0.4)', icon: VoteIcon, fontWeight: 400 };
        case "ability":
            return { color: '#d8b4fe', bgcolor: 'rgba(168, 85, 247, 0.15)', borderColor: 'rgba(168, 85, 247, 0.5)', icon: AbilityIcon, fontWeight: 500 };
        case "win":
            return { color: '#fde047', bgcolor: 'rgba(234, 179, 8, 0.2)', borderColor: 'rgba(234, 179, 8, 0.9)', icon: WinIcon, fontWeight: 800 };
        case "phase_change":
        case "system":
        default:
            return { color: '#cbd5e1', bgcolor: 'rgba(255, 255, 255, 0.05)', borderColor: 'rgba(255, 255, 255, 0.15)', icon: SystemIcon, fontWeight: 400 };
    }
}

export default function PlayGame() {
    const { id: templateId } = useParams();
    const navigate = useNavigate();
    const [gameState, setGameState] = useState<GameState | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);
    const [exitDialogOpen, setExitDialogOpen] = useState(false);
    const logsEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (logsEndRef.current) {
            logsEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [gameState?.logs?.length]);

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
        <Box sx={{ height: '100%', backgroundImage: `url(${bgImage})`, backgroundSize: 'cover', backgroundPosition: 'center', position: 'relative', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(10, 15, 25, 0.55)' }} />
            <CircularProgress sx={{ color: '#3b82f6', zIndex: 1 }} size={60} />
        </Box>
    );

    if (error) return (
        <Box sx={{ height: '100%', backgroundImage: `url(${bgImage})`, backgroundSize: 'cover', backgroundPosition: 'center', position: 'relative', p: 4 }}>
            <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(10, 15, 25, 0.55)' }} />
            <Alert severity="error" sx={{ position: 'relative', zIndex: 1 }}>{error}</Alert>
        </Box>
    );

    if (!gameState) return (
        <Box sx={{ height: '100%', backgroundImage: `url(${bgImage})`, backgroundSize: 'cover', backgroundPosition: 'center', position: 'relative', p: 4 }}>
            <Box sx={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(10, 15, 25, 0.55)' }} />
            <Alert severity="warning" sx={{ position: 'relative', zIndex: 1 }}>Game state not found.</Alert>
        </Box>
    );

    const phaseGuidance = getPhaseGuidance(gameState);
    const alivePlayers = gameState.players.filter((p) => p.is_alive);
    const eliminatedPlayers = gameState.players.filter((p) => !p.is_alive);
    const handleExitSoloGame = () => {
        setExitDialogOpen(true);
    };

    const confirmExit = () => {
        setExitDialogOpen(false);
        navigate("/");
    };

    return (
        <Box 
            sx={{ 
                height: '100%', 
                overflow: 'hidden',
                backgroundImage: `url(${bgImage})`, 
                backgroundSize: 'cover', 
                backgroundPosition: 'center', 
                backgroundAttachment: 'fixed',
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                '&::before': {
                    content: '""',
                    position: 'absolute',    
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(10, 15, 25, 0.55)', 
                    zIndex: 0
                }
            }}
        >
            <Box sx={{ position: 'relative', zIndex: 1, p: { xs: 2, lg: 3 }, width: '100%', maxWidth: 1600, mx: 'auto', display: 'flex', flexDirection: 'column', flexGrow: 1, overflow: 'hidden' }}>
                <Paper sx={{ 
                    p: 3, 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    bgcolor: 'rgba(30, 41, 59, 0.6)', 
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                    borderRadius: 3,
                    mb: 3
                }}>
                    <Box>
                        <Typography variant="h4" fontWeight={800} sx={{ 
                            background: 'linear-gradient(45deg, #f3f4f6, #9ca3af)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                        }}>
                            {gameState.phase === "GAME_OVER"
                                ? "Game Over"
                                : `${gameState.phase === "VOTING" ? "Voting" : gameState.phase === "NIGHT" ? "Night" : gameState.phase === "DAY" ? "Day" : gameState.phase} — Turn ${gameState.turn}`}
                        </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="h6" color="white" fontWeight={700}>
                            {gameState.me.name}
                        </Typography>
                        <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                            {gameState.me.role} ({gameState.me.alignment})
                        </Typography>
                        <Typography variant="body2" fontWeight={600} sx={{ color: gameState.me.is_alive ? '#10b981' : '#ef4444' }}>
                            {gameState.me.is_alive ? "Alive" : "Dead"}
                        </Typography>
                        <Button
                            variant="outlined"
                            size="small"
                            onClick={handleExitSoloGame}
                            sx={{ mt: 1, color: 'white', borderColor: 'rgba(255,255,255,0.35)' }}
                        >
                            Exit Game
                        </Button>
                    </Box>
                </Paper>

                <Alert severity={phaseGuidance.severity} sx={{ 
                    mb: 3, 
                    bgcolor: 'rgba(15, 23, 42, 0.8)', 
                    backdropFilter: 'blur(10px)',
                    color: 'white',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 2,
                    '& .MuiAlert-icon': { color: phaseGuidance.severity === 'info' ? '#60a5fa' : undefined }
                }}>
                    <Typography variant="subtitle2" fontWeight={700}>{phaseGuidance.title}</Typography>
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.8)' }}>{phaseGuidance.message}</Typography>
                </Alert>

                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr 1fr 1.25fr' }, gap: 3, flexGrow: 1, minHeight: 0, overflow: 'hidden', pb: 2 }}>
                    {/* Column 1: Logs */}
                    <Card sx={{ 
                        display: 'flex', flexDirection: 'column', 
                        bgcolor: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(12px)',
                        border: '1px solid rgba(255,255,255,0.1)', color: 'white',
                        borderRadius: 3, height: '100%', overflow: 'hidden'
                    }}>
                        <CardContent sx={{ flexGrow: 1, overflowY: 'auto', p: 3, '&::-webkit-scrollbar': { width: '8px' }, '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(255,255,255,0.2)', borderRadius: '4px' } }}>
                            <Typography variant="h6" fontWeight={700} gutterBottom sx={{ color: '#60a5fa' }}>Game Logs</Typography>
                            <Divider sx={{ mb: 2, borderColor: 'rgba(255,255,255,0.1)' }} />
                            <List disablePadding>
                                {gameState.logs.map((log, index) => {
                                    if (log.type === "phase_change") {
                                        return (
                                            <Box key={index} sx={{ my: 3, position: 'relative' }}>
                                                <Divider sx={{ '&::before, &::after': { borderColor: 'rgba(255,255,255,0.2)' } }}>
                                                    <Box sx={{ 
                                                        bgcolor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.2)', 
                                                        px: 2, py: 0.5, borderRadius: 5, backdropFilter: 'blur(4px)' 
                                                    }}>
                                                        <Typography variant="caption" sx={{
                                                            color: '#e2e8f0', fontWeight: 800, letterSpacing: 2, textTransform: 'uppercase'
                                                        }}>
                                                            {log.message}
                                                        </Typography>
                                                    </Box>
                                                </Divider>
                                            </Box>
                                        );
                                    }
                                    const style = getLogStyle(log.type);
                                    const IconComponent = style.icon;
                                    return (
                                        <Box key={index} sx={{ 
                                            mb: 1.5, p: 1.5, borderRadius: 2, 
                                            bgcolor: style.bgcolor, 
                                            borderLeft: '4px solid', 
                                            borderLeftColor: style.borderColor,
                                            borderTop: '1px solid rgba(255,255,255,0.05)',
                                            borderRight: '1px solid rgba(255,255,255,0.05)',
                                            borderBottom: '1px solid rgba(255,255,255,0.05)',
                                            display: 'flex', alignItems: 'flex-start', gap: 1.5
                                        }}>
                                            <IconComponent sx={{ color: style.color, fontSize: 20, mt: 0.2 }} />
                                            <Typography variant="body2" sx={{ 
                                                color: style.color, 
                                                fontWeight: style.fontWeight,
                                                lineHeight: 1.5,
                                                wordBreak: 'break-word'
                                            }}>
                                                {formatLogMessage(log.message, gameState.me.name)}
                                            </Typography>
                                        </Box>
                                    );
                                })}
                                <div ref={logsEndRef} />
                            </List>
                        </CardContent>
                    </Card>

                    {/* Column 2: Players */}
                    <Card sx={{ 
                        display: 'flex', flexDirection: 'column', 
                        bgcolor: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(12px)',
                        border: '1px solid rgba(255,255,255,0.1)', color: 'white',
                        borderRadius: 3, height: '100%', overflow: 'hidden'
                    }}>
                        <CardContent sx={{ flexGrow: 1, overflowY: 'auto', p: 3, '&::-webkit-scrollbar': { width: '8px' }, '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(255,255,255,0.2)', borderRadius: '4px' } }}>
                            <Typography variant="h6" fontWeight={700} gutterBottom sx={{ color: '#60a5fa' }}>Players</Typography>
                            <Divider sx={{ mb: 2, borderColor: 'rgba(255,255,255,0.1)' }} />
                            <Typography variant="subtitle2" sx={{ color: '#10b981', mb: 1 }}>
                                Alive ({alivePlayers.length})
                            </Typography>
                            <List disablePadding sx={{ mb: eliminatedPlayers.length > 0 ? 2 : 0 }}>
                                {alivePlayers.map(p => (
                                    <ListItem key={p.name} disablePadding sx={{ mb: 1, bgcolor: 'rgba(255,255,255,0.03)', p: 1, borderRadius: 2 }}>
                                        <ListItemText
                                            primary={p.name === gameState.me.name ? `${p.name} (You)` : p.name}
                                            secondary={p.role !== "Unknown" ? p.role : undefined}
                                            primaryTypographyProps={{
                                                fontWeight: p.name === gameState.me.name ? 700 : 400,
                                                color: p.name === gameState.me.name ? '#60a5fa' : 'white'
                                            }}
                                            secondaryTypographyProps={{ color: '#10b981' }}
                                        />
                                    </ListItem>
                                ))}
                            </List>

                            {eliminatedPlayers.length > 0 && (
                                <>
                                    <Typography variant="subtitle2" sx={{ color: '#ef4444', mb: 1 }}>
                                        Eliminated ({eliminatedPlayers.length})
                                    </Typography>
                                    <List disablePadding>
                                        {eliminatedPlayers.map(p => (
                                            <ListItem key={p.name} disablePadding sx={{ mb: 1, bgcolor: 'rgba(0,0,0,0.2)', p: 1, borderRadius: 2 }}>
                                                <ListItemText
                                                    primary={p.name === gameState.me.name ? `${p.name} (You)` : p.name}
                                                    secondary={p.role !== "Unknown" ? p.role : undefined}
                                                    sx={{
                                                        textDecoration: 'line-through',
                                                        color: 'rgba(255,255,255,0.4)'
                                                    }}
                                                    primaryTypographyProps={{
                                                        fontWeight: p.name === gameState.me.name ? 700 : 400
                                                    }}
                                                    secondaryTypographyProps={{ color: '#ef4444' }}
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                </>
                            )}
                        </CardContent>
                    </Card>

                    {/* Column 3: Actions */}
                    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
                        {gameState.phase !== "GAME_OVER" ? (
                            <Paper sx={{ 
                                p: 3, 
                                bgcolor: 'rgba(15, 23, 42, 0.7)', 
                                backdropFilter: 'blur(12px)',
                                border: '1px solid rgba(255,255,255,0.1)', 
                                color: 'white',
                                borderRadius: 3,
                                flexGrow: 1,
                                overflowY: 'auto'
                            }}>
                                <Typography variant="h6" fontWeight={700} gutterBottom sx={{ color: '#60a5fa' }}>Command Center</Typography>
                                <Divider sx={{ mb: 3, borderColor: 'rgba(255,255,255,0.1)' }} />

                                {!gameState.me.is_alive ? (
                                    <Box sx={{ textAlign: 'center', p: 4, bgcolor: 'rgba(0,0,0,0.3)', borderRadius: 2 }}>
                                        <Typography sx={{ color: 'rgba(255,255,255,0.7)' }}>You are dead. Wait for the game to finish.</Typography>
                                    </Box>
                                ) : (
                                    <Box>
                                        {gameState.phase === "NIGHT" && (
                                            <form onSubmit={submitNightAction}>
                                                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 3 }}>
                                                    {gameState.me.abilities.length > 0
                                                        ? "Night actions happen in secret. Pick an ability and target."
                                                        : "You have no night actions this turn. Submit to continue."}
                                                </Typography>
                                                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                                    {currentAbilities.length > 0 ? (
                                                        <>
                                                            <FormControl fullWidth>
                                                                <Select
                                                                    value={selectedAbility}
                                                                    onChange={e => setSelectedAbility(Number(e.target.value))}
                                                                    disabled={isSubmitting}
                                                                    sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' }, '& .MuiSvgIcon-root': { color: 'white' } }}
                                                                >
                                                                    {currentAbilities.map(ab => (
                                                                        <MenuItem key={ab.index} value={ab.index}>{ab.name}</MenuItem>
                                                                    ))}
                                                                </Select>
                                                            </FormControl>

                                                            <FormControl fullWidth>
                                                                <Select
                                                                    value={selectedAbilityTarget}
                                                                    onChange={e => setSelectedAbilityTarget(e.target.value)}
                                                                    displayEmpty
                                                                    required
                                                                    disabled={isSubmitting}
                                                                    sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' }, '& .MuiSvgIcon-root': { color: 'white' } }}
                                                                >
                                                                    <MenuItem value="" disabled>Select Target</MenuItem>
                                                                    {gameState.players.filter(p => p.is_alive).map(p => (
                                                                        <MenuItem key={p.name} value={p.name}>{p.name}</MenuItem>
                                                                    ))}
                                                                </Select>
                                                            </FormControl>
                                                            <Button type="submit" variant="contained" size="large" sx={{ bgcolor: '#10b981', '&:hover': { bgcolor: '#059669' }, mt: 2 }} disabled={isSubmitting}>
                                                                {isSubmitting ? "Submitting..." : "Use Ability"}
                                                            </Button>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Box sx={{ textAlign: 'center', p: 3, bgcolor: 'rgba(255,255,255,0.05)', borderRadius: 2 }}>
                                                                <Typography sx={{ mb: 3 }}>No abilities to use tonight.</Typography>
                                                                <Button type="submit" variant="contained" size="large" sx={{ bgcolor: '#4b5563', '&:hover': { bgcolor: '#374151' } }} disabled={isSubmitting}>
                                                                    {isSubmitting ? "Submitting..." : "Go to Sleep"}
                                                                </Button>
                                                            </Box>
                                                        </>
                                                    )}
                                                </Box>
                                            </form>
                                        )}

                                        {gameState.phase === "VOTING" && (
                                            <Box>
                                                {votingSubPhase === 'ABILITY' && currentAbilities.length > 0 ? (
                                                    <Box sx={{ mb: 3, p: 3, border: '1px solid rgba(59, 130, 246, 0.5)', borderRadius: 3, bgcolor: 'rgba(59, 130, 246, 0.05)' }}>
                                                        <Typography variant="h6" gutterBottom sx={{ color: '#60a5fa' }}>Phase 1: Vote Manipulation</Typography>
                                                        <Typography variant="body2" sx={{ mb: 3, color: 'rgba(255,255,255,0.7)' }}>
                                                            Select an ability to use before final voting begins. You can only use one ability per voting round.
                                                        </Typography>
                                                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                                            <FormControl fullWidth>
                                                                <Select
                                                                    value={selectedAbility}
                                                                    onChange={e => setSelectedAbility(Number(e.target.value))}
                                                                    disabled={isSubmitting}
                                                                    sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' }, '& .MuiSvgIcon-root': { color: 'white' } }}
                                                                >
                                                                    {currentAbilities.map(ab => (
                                                                        <MenuItem key={ab.index} value={ab.index}>{ab.name}</MenuItem>
                                                                    ))}
                                                                </Select>
                                                            </FormControl>
                                                            <FormControl fullWidth>
                                                                <Select
                                                                    value={selectedAbilityTarget}
                                                                    onChange={e => setSelectedAbilityTarget(e.target.value)}
                                                                    displayEmpty
                                                                    disabled={isSubmitting}
                                                                    sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' }, '& .MuiSvgIcon-root': { color: 'white' } }}
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
                                                                size="large"
                                                                sx={{ bgcolor: '#3b82f6', '&:hover': { bgcolor: '#2563eb' } }}
                                                                disabled={isSubmitting || !selectedAbilityTarget}
                                                            >
                                                                Use Ability
                                                            </Button>
                                                            <Button
                                                                onClick={() => setVotingSubPhase('VOTE')}
                                                                variant="text"
                                                                sx={{ color: '#9ca3af' }}
                                                                disabled={isSubmitting}
                                                            >
                                                                Skip to Vote
                                                            </Button>
                                                        </Box>
                                                    </Box>
                                                ) : (
                                                    <form onSubmit={submitVoteAction}>
                                                        <Box sx={{ p: 3, border: '1px solid rgba(239, 68, 68, 0.5)', borderRadius: 3, bgcolor: 'rgba(239, 68, 68, 0.05)' }}>
                                                            <Typography variant="h6" gutterBottom sx={{ color: '#f87171' }}>Phase 2: Final Vote</Typography>
                                                            <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', mb: 3 }}>
                                                                Manipulation phase is over. Cast your final vote for elimination.
                                                            </Typography>
                                                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                                                                <FormControl fullWidth>
                                                                    <Select
                                                                        value={selectedVoteTarget}
                                                                        onChange={e => setSelectedVoteTarget(e.target.value)}
                                                                        displayEmpty
                                                                        required
                                                                        disabled={isSubmitting}
                                                                        sx={{ color: 'white', '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' }, '& .MuiSvgIcon-root': { color: 'white' } }}
                                                                    >
                                                                        <MenuItem value="" disabled>Select Target</MenuItem>
                                                                        {gameState.players.filter(p => p.is_alive).map(p => (
                                                                            <MenuItem key={p.name} value={p.name}>{p.name}</MenuItem>
                                                                        ))}
                                                                    </Select>
                                                                </FormControl>
                                                                <Button type="submit" variant="contained" size="large" sx={{ bgcolor: '#ef4444', '&:hover': { bgcolor: '#dc2626' } }} disabled={isSubmitting}>
                                                                    {isSubmitting ? "Submit Vote" : "Confirm Vote"}
                                                                </Button>
                                                            </Box>
                                                        </Box>
                                                    </form>
                                                )}
                                            </Box>
                                        )}

                                        {gameState.phase === "DAY" && (
                                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, textAlign: 'center', p: 4, bgcolor: 'rgba(255,255,255,0.05)', borderRadius: 2 }}>
                                                <Typography sx={{ color: 'rgba(255,255,255,0.9)' }}>Read the logs and discuss. When you are ready to vote, proceed to end the day.</Typography>
                                                <Button onClick={() => void handleAction(null)} variant="contained" size="large" sx={{ bgcolor: '#f59e0b', '&:hover': { bgcolor: '#d97706' } }} disabled={isSubmitting}>
                                                    {isSubmitting ? "Submitting..." : "End Day"}
                                                </Button>
                                            </Box>
                                        )}
                                    </Box>
                                )}
                            </Paper>
                        ) : (
                            <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'rgba(16, 185, 129, 0.2)', backdropFilter: 'blur(12px)', border: '1px solid rgba(16, 185, 129, 0.5)', color: 'white', borderRadius: 3, flexGrow: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                                <Typography variant="h3" fontWeight={800} gutterBottom sx={{ color: '#10b981' }}>Game Over!</Typography>
                                <Typography sx={{ mb: 4, color: 'rgba(255,255,255,0.8)' }}>Thanks for playing. Check the logs to see how it all went down.</Typography>
                                <Button
                                    variant="contained"
                                    onClick={() => navigate("/")}
                                    sx={{ bgcolor: '#10b981', '&:hover': { bgcolor: '#059669' }, alignSelf: 'center', px: 4, py: 1.5 }}
                                >
                                    Back to Dashboard
                                </Button>
                            </Paper>
                        )}
                    </Box>
                </Box>
            </Box>

            <Snackbar
                open={Boolean(actionError)}
                autoHideDuration={5000}
                onClose={() => setActionError(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={() => setActionError(null)} severity="error" sx={{ width: '100%', borderRadius: 2, boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
                    {actionError}
                </Alert>
            </Snackbar>

            <Dialog
                open={exitDialogOpen}
                onClose={() => setExitDialogOpen(false)}
            >
                <DialogTitle>Exit Solo Game?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Your current run will be lost. Are you sure you want to exit?
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setExitDialogOpen(false)} color="secondary">Cancel</Button>
                    <Button onClick={confirmExit} color="error" variant="contained">Exit</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
