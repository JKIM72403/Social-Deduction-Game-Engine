import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { API } from "../services/api";
import {
    Box, Typography, Card, CardContent, Button, FormControl, Select, MenuItem,
    Paper, List, ListItem, ListItemText, CircularProgress, Divider, Alert
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

export default function PlayGame() {
    const { id: templateId } = useParams();
    const navigate = useNavigate();
    const [gameState, setGameState] = useState<GameState | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Form states
    const [selectedAbility, setSelectedAbility] = useState<number>(0);
    const [selectedTarget, setSelectedTarget] = useState<string>("");

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

    const handleAction = (actionData: any) => {
        if (!gameState) return;
        API.post(`/game-sessions/${gameState.session_id}/act/`, {
            user_name: "You",
            action: actionData
        })
            .then((res) => {
                setGameState(res.data);
            })
            .catch((err) => console.error("Action failed", err));
    };

    const submitNightAction = (e: React.FormEvent) => {
        e.preventDefault();
        if (gameState?.me.abilities.length === 0) {
            handleAction(null); // Just skip
            return;
        }
        handleAction({
            ability_index: selectedAbility,
            target: selectedTarget
        });
    };

    const submitVoteAction = (e: React.FormEvent) => {
        e.preventDefault();
        handleAction({
            action: "vote",
            target: selectedTarget
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
                        <List disablePadding>
                            {gameState.players.map(p => (
                                <ListItem key={p.name} disablePadding sx={{ mb: 1 }}>
                                    <ListItemText 
                                        primary={p.name} 
                                        secondary={!p.is_alive ? p.role : null}
                                        sx={{ 
                                            textDecoration: p.is_alive ? 'none' : 'line-through',
                                            color: p.is_alive ? 'text.primary' : 'text.disabled'
                                        }}
                                        secondaryTypographyProps={{ color: 'error.main' }}
                                    />
                                </ListItem>
                            ))}
                        </List>
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
                                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                        {gameState.me.abilities.length > 0 ? (
                                            <>
                                                <FormControl size="small" sx={{ minWidth: 150 }}>
                                                    <Select
                                                        value={selectedAbility}
                                                        onChange={e => setSelectedAbility(Number(e.target.value))}
                                                    >
                                                        {gameState.me.abilities.map(ab => (
                                                            <MenuItem key={ab.index} value={ab.index}>{ab.name}</MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                                
                                                <FormControl size="small" sx={{ minWidth: 150 }}>
                                                    <Select
                                                        value={selectedTarget}
                                                        onChange={e => setSelectedTarget(e.target.value)}
                                                        displayEmpty
                                                        required
                                                    >
                                                        <MenuItem value="" disabled>Select Target</MenuItem>
                                                        {gameState.players.filter(p => p.is_alive).map(p => (
                                                            <MenuItem key={p.name} value={p.name}>{p.name}</MenuItem>
                                                        ))}
                                                    </Select>
                                                </FormControl>
                                                <Button type="submit" variant="contained" color="success">
                                                    Use Ability
                                                </Button>
                                            </>
                                        ) : (
                                            <>
                                                <Typography>No abilities to use tonight.</Typography>
                                                <Button type="submit" variant="contained" color="inherit">
                                                    Sleep
                                                </Button>
                                            </>
                                        )}
                                    </Box>
                                </form>
                            )}

                            {gameState.phase === "VOTING" && (
                                <form onSubmit={submitVoteAction}>
                                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                        <FormControl size="small" sx={{ minWidth: 150 }}>
                                            <Select
                                                value={selectedTarget}
                                                onChange={e => setSelectedTarget(e.target.value)}
                                                displayEmpty
                                                required
                                            >
                                                <MenuItem value="" disabled>Select Target</MenuItem>
                                                {gameState.players.filter(p => p.is_alive).map(p => (
                                                    <MenuItem key={p.name} value={p.name}>{p.name}</MenuItem>
                                                ))}
                                            </Select>
                                        </FormControl>
                                        <Button type="submit" variant="contained" color="error">
                                            Vote to Eliminate
                                        </Button>
                                    </Box>
                                </form>
                            )}

                            {gameState.phase === "DAY" && (
                                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                                    <Typography>Discuss with the town.</Typography>
                                    <Button onClick={() => handleAction(null)} variant="contained" color="warning">
                                        End Day
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
        </Box>
    );
}
