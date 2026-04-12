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

    return (
        <Box sx={{ p: 4, maxWidth: 1200, mx: 'auto' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2, alignItems: { xs: 'flex-start', md: 'center' }, flexDirection: { xs: 'column', md: 'row' } }}>
                <Box>
                    <Typography variant="h4" gutterBottom>
                        Game Templates
                    </Typography>
                    <Typography variant="body1" color="text.secondary" gutterBottom>
                        Create and play solo or multiplayer social deduction games!
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <TextField
                        size="small"
                        label="Search"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        sx={{ minWidth: 200 }}
                    />
                    <FormControl size="small" sx={{ minWidth: 200 }}>
                        <InputLabel>Sort By</InputLabel>
                        <Select
                            value={sortBy}
                            label="Sort By"
                            onChange={(e: SelectChangeEvent) => setSortBy(e.target.value as SortOption)}
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
                        <Button variant="outlined" color="secondary" component={RouterLink} to="/multiplayer">
                            Join Lobby by Code
                        </Button>
                    )}
                </Box>
            </Box>

            <Box sx={{ mt: 4 }}>
                {loading ? (
                    <CircularProgress />
                ) : games.length === 0 ? (
                    <Typography>No games found. Create one!</Typography>
                ) : (
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' }, gap: 3 }}>
                        {sortedGames.map((game) => (
                            <Box key={game.id}>
                                <Card elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                                    <CardContent sx={{ flexGrow: 1 }}>
                                        <Typography variant="h6" component="div">
                                            {game.name}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Players: {game.min_players} - {game.max_players}
                                        </Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            by {game.creator_name || "Unknown"}
                                        </Typography>
                                    </CardContent>
                                    <CardActions sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <Box sx={{ display: 'flex', gap: 1 }}>
                                            <Button
                                                size="small"
                                                variant="outlined"
                                                color="primary"
                                                component={RouterLink}
                                                to={`/play-game/${game.id}`}
                                            >
                                                Play Solo
                                            </Button>
                                            {user && (
                                                <Button
                                                    size="small"
                                                    variant="contained"
                                                    color="secondary"
                                                    onClick={() => void handleHostLobby(game)}
                                                    disabled={creatingSessionFor === game.id}
                                                >
                                                    {creatingSessionFor === game.id ? "Creating..." : "Host Lobby"}
                                                </Button>
                                            )}
                                            {isOwner(game) && (
                                                <Button
                                                    size="small"
                                                    variant="outlined"
                                                    color="secondary"
                                                    component={RouterLink}
                                                    to={`/edit-game/${game.id}`}
                                                >
                                                    Edit
                                                </Button>
                                            )}
                                        </Box>
                                        {isOwner(game) && (
                                            <Button
                                                size="small"
                                                color="error"
                                                onClick={() => setDeleteGame(game)}
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
            >
                <DialogTitle>Delete Game?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Are you sure you want to permanently delete "{deleteGame?.name}"? This action cannot be undone.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteGame(null)} color="secondary">Cancel</Button>
                    <Button onClick={confirmDeleteGame} color="error" variant="contained">Delete</Button>
                </DialogActions>
            </Dialog>

            <Snackbar
                open={snackbar.open}
                autoHideDuration={6000}
                onClose={handleSnackbarClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={handleSnackbarClose} severity={snackbar.severity} sx={{ width: '100%' }}>
                    {snackbar.message}
                </Alert>
            </Snackbar>
        </Box>
    );
}
