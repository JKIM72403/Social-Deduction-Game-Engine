import { useState, useEffect, useMemo } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import {
    Box, Typography, Card, CardContent, CardActions, Button, CircularProgress,
    FormControl, InputLabel, Select, MenuItem, TextField,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { API } from "../services/api";
import { useAuth } from "../contexts/AuthContext";
import bgImage from '../assets/mafia_bg.png';
import { createSession } from "../services/sessions";

type GameTemplate = {
    id: number;
    name: string;
    min_players: number;
    max_players: number;
    created_at: string;
    creator_id: number | null;
    creator_name: string | null;
};

type SortOption = 'name-asc' | 'name-desc' | 'date-newest' | 'date-oldest' | 'players-asc' | 'players-desc';

export default function Home() {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [games, setGames] = useState<GameTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [creatingSessionFor, setCreatingSessionFor] = useState<number | null>(null);
    const [sortBy, setSortBy] = useState<SortOption>('name-asc');
    const [searchQuery, setSearchQuery] = useState('');

    const [deleteGame, setDeleteGame] = useState<GameTemplate | null>(null);
    const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

    useEffect(() => {
        API.get("/game-templates/")
            .then((res) => {
                setGames(res.data);
                setLoading(false);
            })
            .catch((err) => {
                console.error("Failed to load games", err);
                setLoading(false);
            });
    }, []);

    const sortedGames = useMemo(() => {
        const query = searchQuery.toLowerCase();
        const filtered = games.filter(g => g.name.toLowerCase().includes(query));
        const sorted = [...filtered];
        switch (sortBy) {
            case 'name-asc':
                sorted.sort((a, b) => a.name.localeCompare(b.name));
                break;
            case 'name-desc':
                sorted.sort((a, b) => b.name.localeCompare(a.name));
                break;
            case 'date-newest':
                sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                break;
            case 'date-oldest':
                sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
                break;
            case 'players-asc':
                sorted.sort((a, b) => a.max_players - b.max_players);
                break;
            case 'players-desc':
                sorted.sort((a, b) => b.max_players - a.max_players);
                break;
        }
        return sorted;
    }, [games, sortBy, searchQuery]);

    const handleSnackbarClose = () => {
        setSnackbar(prev => ({ ...prev, open: false }));
    };

    const confirmDeleteGame = async () => {
        if (!deleteGame) return;
        try {
            await API.delete(`/game-templates/${deleteGame.id}/`);
            setGames(prev => prev.filter(g => g.id !== deleteGame.id));
            setSnackbar({ open: true, message: "Game Deleted Successfully!", severity: 'success' });
        } catch (err) {
            console.error(err);
            setSnackbar({ open: true, message: "Failed to delete game.", severity: 'error' });
        } finally {
            setDeleteGame(null);
        }
    };

    const isOwner = (game: GameTemplate) => user !== null && game.creator_id === user.id;

    const handleHostLobby = async (game: GameTemplate) => {
        if (!user) {
            navigate("/login");
            return;
        }

        setCreatingSessionFor(game.id);
        try {
            const snapshot = await createSession(game.id, user.username);
            navigate(`/sessions/${snapshot.session.id}`);
        } catch (err: any) {
            console.error(err);
            const message =
                err?.response?.data?.error ||
                "Unable to create a lobby for that template right now.";
            setSnackbar({ open: true, message, severity: 'error' });
        } finally {
            setCreatingSessionFor(null);
        }
    };
    if (!user) {
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
                    justifyContent: 'center',
                    alignItems: 'center',
                    zIndex: 0,
                    '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 0, left: 0, right: 0, bottom: 0,
                        backgroundColor: 'rgba(10, 15, 25, 0.70)', 
                        backdropFilter: 'blur(3px)',
                        zIndex: -1
                    }
                }}
            >
                <Box sx={{ textAlign: 'center', color: 'white', maxWidth: '800px', p: 4 }}>
                    <Typography variant="h2" fontWeight={900} gutterBottom sx={{ letterSpacing: 2, textShadow: '0 4px 12px rgba(0,0,0,0.5)', fontFamily: 'system-ui, -apple-system' }}>
                        SOCIAL DEDUCTION ENGINE
                    </Typography>
                    <Typography variant="h6" sx={{ mb: 6, color: 'rgba(255,255,255,0.7)', fontWeight: 300 }}>
                        Design, play, and administrate custom games of deception and strategy with friends in real-time.
                    </Typography>
                    
                    <Box sx={{ display: 'flex', gap: 3, justifyContent: 'center' }}>
                        <Button 
                            variant="contained" 
                            color="primary" 
                            size="large"
                            component={RouterLink} 
                            to="/signup"
                            sx={{ px: 5, py: 1.5, fontSize: '1.1rem', borderRadius: 2 }}
                        >
                            Get Started
                        </Button>
                        <Button 
                            variant="outlined" 
                            size="large"
                            component={RouterLink} 
                            to="/login"
                            sx={{ px: 5, py: 1.5, fontSize: '1.1rem', borderRadius: 2, borderColor: 'rgba(255,255,255,0.4)', color: 'white', '&:hover': { borderColor: 'white' } }}
                        >
                            Log In
                        </Button>
                    </Box>
                </Box>
            </Box>
        );
    }

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
                    position: 'absolute',    // Cover the background
                    top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(10, 15, 25, 0.55)', // Dark overlay so cards stand out
                    zIndex: 0
                }
            }}
        >
            <Box sx={{ position: 'relative', zIndex: 1, p: { xs: 2, md: 4 }, maxWidth: 1200, mx: 'auto', width: '100%' }}>
                {/* Header section with glassmorphism */}
                <Box sx={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    gap: 2, 
                    alignItems: { xs: 'flex-start', md: 'center' }, 
                    flexDirection: { xs: 'column', md: 'row' },
                    bgcolor: 'rgba(30, 41, 59, 0.6)', 
                    backdropFilter: 'blur(12px)',
                    p: 4,
                    borderRadius: 3,
                    border: '1px solid rgba(255,255,255,0.1)',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
                    mb: 4
                }}>
                    <Box>
                        <Typography variant="h4" fontWeight={700} sx={{ 
                            background: 'linear-gradient(45deg, #f3f4f6, #9ca3af)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            textShadow: '0px 2px 10px rgba(0,0,0,0.5)',
                            mb: 1
                        }}>
                            Game Templates
                        </Typography>
                        <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                            Create and play solo or multiplayer social deduction games!
                        </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
                        <TextField
                            size="small"
                            label="Search"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            sx={{ 
                                minWidth: 200, 
                                '& .MuiOutlinedInput-root': { color: 'white', '& fieldset': { borderColor: 'rgba(255,255,255,0.3)' }, '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.5)' } },
                                '& .MuiInputLabel-root': { color: 'rgba(255,255,255,0.7)' }
                            }}
                        />
                        <FormControl size="small" sx={{ minWidth: 200 }}>
                            <InputLabel sx={{ color: 'rgba(255,255,255,0.7)' }}>Sort By</InputLabel>
                            <Select
                                value={sortBy}
                                label="Sort By"
                                onChange={(e: SelectChangeEvent) => setSortBy(e.target.value as SortOption)}
                                sx={{ 
                                    color: 'white', 
                                    '& .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.3)' }, 
                                    '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.5)' },
                                    '& .MuiSvgIcon-root': { color: 'white' }
                                }}
                            >
                                <MenuItem value="name-asc">Name (A-Z)</MenuItem>
                                <MenuItem value="name-desc">Name (Z-A)</MenuItem>
                                <MenuItem value="date-newest">Newest First</MenuItem>
                                <MenuItem value="date-oldest">Oldest First</MenuItem>
                                <MenuItem value="players-asc">Max Players (Low-High)</MenuItem>
                                <MenuItem value="players-desc">Max Players (High-Low)</MenuItem>
                            </Select>
                        </FormControl>
                        {user && (
                            <Button 
                                variant="contained" 
                                component={RouterLink} 
                                to="/multiplayer"
                                sx={{ 
                                    background: 'linear-gradient(45deg, #10b981, #059669)',
                                    boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)',
                                    fontWeight: 600,
                                    '&:hover': { background: 'linear-gradient(45deg, #059669, #047857)' }
                                }}
                            >
                                Join Lobby by Code
                            </Button>
                        )}
                    </Box>
                </Box>

                <Box sx={{ mt: 2 }}>
                    {loading ? (
                        <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
                            <CircularProgress sx={{ color: '#3b82f6' }} size={60} />
                        </Box>
                    ) : games.length === 0 ? (
                        <Box sx={{ textAlign: 'center', p: 6, bgcolor: 'rgba(30, 41, 59, 0.6)', backdropFilter: 'blur(12px)', borderRadius: 3, border: '1px solid rgba(255,255,255,0.1)' }}>
                            <Typography variant="h5" color="white" gutterBottom>No games found.</Typography>
                            <Typography sx={{ color: 'rgba(255,255,255,0.7)', mb: 3 }}>Create a template to host your first match!</Typography>
                        </Box>
                    ) : (
                        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' }, gap: 4 }}>
                            {sortedGames.map((game) => (
                                <Box key={game.id}>
                                    <Card sx={{ 
                                        height: '100%', 
                                        display: 'flex', 
                                        flexDirection: 'column', 
                                        bgcolor: 'rgba(15, 23, 42, 0.7)',
                                        backdropFilter: 'blur(12px)',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        color: 'white',
                                        transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
                                        '&:hover': {
                                            transform: 'translateY(-5px)',
                                            boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
                                            borderColor: 'rgba(59, 130, 246, 0.5)'
                                        }
                                    }}>
                                        <CardContent sx={{ flexGrow: 1 }}>
                                            <Typography variant="h5" fontWeight={700} gutterBottom sx={{ color: '#60a5fa' }}>
                                                {game.name}
                                            </Typography>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                                                <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)' }}>
                                                    Players: <span style={{ color: 'white', fontWeight: 600 }}>{game.min_players} - {game.max_players}</span>
                                                </Typography>
                                            </Box>
                                            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)' }}>
                                                by <span style={{ color: '#9ca3af' }}>{game.creator_name || "Unknown"}</span>
                                            </Typography>
                                        </CardContent>
                                        <CardActions sx={{ 
                                            display: 'flex', 
                                            justifyContent: 'space-between',
                                            borderTop: '1px solid rgba(255,255,255,0.05)',
                                            p: 2,
                                            bgcolor: 'rgba(0,0,0,0.2)'
                                        }}>
                                            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
                                                <Button
                                                    size="small"
                                                    variant="outlined"
                                                    component={RouterLink}
                                                    to={`/play-game/${game.id}`}
                                                    sx={{ 
                                                        color: 'white', 
                                                        borderColor: 'rgba(255,255,255,0.3)',
                                                        '&:hover': { borderColor: 'white', bgcolor: 'rgba(255,255,255,0.1)' }
                                                    }}
                                                >
                                                    Play Solo
                                                </Button>
                                                {user && (
                                                    <Button
                                                        size="small"
                                                        variant="contained"
                                                        onClick={() => void handleHostLobby(game)}
                                                        disabled={creatingSessionFor === game.id}
                                                        sx={{ 
                                                            bgcolor: '#3b82f6', 
                                                            '&:hover': { bgcolor: '#2563eb' }
                                                        }}
                                                    >
                                                        {creatingSessionFor === game.id ? "Creating..." : "Host Lobby"}
                                                    </Button>
                                                )}
                                                {isOwner(game) && (
                                                    <Button
                                                        size="small"
                                                        variant="text"
                                                        component={RouterLink}
                                                        to={`/edit-game/${game.id}`}
                                                        sx={{ color: '#9ca3af', '&:hover': { color: 'white' } }}
                                                    >
                                                        Edit
                                                    </Button>
                                                )}
                                            </Box>
                                            {isOwner(game) && (
                                                <Button
                                                    size="small"
                                                    onClick={() => setDeleteGame(game)}
                                                    sx={{ color: '#ef4444', minWidth: 0, p: 1, '&:hover': { bgcolor: 'rgba(239, 68, 68, 0.1)' } }}
                                                >
                                                    Delete
                                                </Button>
                                            )}
                                        </CardActions>
                                    </Card>
                                </Box>
                            ))}
                        </Box>
                    )}
                </Box>

                <Dialog
                    open={!!deleteGame}
                    onClose={() => setDeleteGame(null)}
                    PaperProps={{
                        sx: {
                            bgcolor: 'rgba(30, 41, 59, 0.95)',
                            backdropFilter: 'blur(10px)',
                            color: 'white',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: 3
                        }
                    }}
                >
                    <DialogTitle sx={{ color: '#ef4444', fontWeight: 700 }}>Delete Game?</DialogTitle>
                    <DialogContent>
                        <DialogContentText sx={{ color: 'rgba(255,255,255,0.8)' }}>
                            Are you sure you want to permanently delete "{deleteGame?.name}"? This action cannot be undone.
                        </DialogContentText>
                    </DialogContent>
                    <DialogActions sx={{ p: 3 }}>
                        <Button onClick={() => setDeleteGame(null)} sx={{ color: 'white' }}>Cancel</Button>
                        <Button onClick={confirmDeleteGame} variant="contained" sx={{ bgcolor: '#ef4444', '&:hover': { bgcolor: '#dc2626' } }}>Delete</Button>
                    </DialogActions>
                </Dialog>

                <Snackbar
                    open={snackbar.open}
                    autoHideDuration={6000}
                    onClose={handleSnackbarClose}
                    anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
                >
                    <Alert onClose={handleSnackbarClose} severity={snackbar.severity} sx={{ width: '100%', borderRadius: 3, boxShadow: '0 8px 32px rgba(0,0,0,0.4)' }}>
                        {snackbar.message}
                    </Alert>
                </Snackbar>
            </Box>
        </Box>
    );
}
