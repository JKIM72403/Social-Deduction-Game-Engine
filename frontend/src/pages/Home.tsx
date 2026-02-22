import { useState, useEffect } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Typography, Card, CardContent, CardActions, Button, CircularProgress } from "@mui/material";
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import { API } from "../services/api";

type GameTemplate = {
    id: number;
    name: string;
    min_players: number;
    max_players: number;
};

export default function Home() {
    const [games, setGames] = useState<GameTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    
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

    return (
        <Box sx={{ p: 4, maxWidth: 1200, mx: 'auto' }}>
            <Typography variant="h4" gutterBottom>
                Game Templates
            </Typography>
            <Typography variant="body1" color="text.secondary" gutterBottom>
                Select a game to modify or create a new one.
            </Typography>

            <Box sx={{ mt: 4 }}>
                {loading ? (
                    <CircularProgress />
                ) : games.length === 0 ? (
                    <Typography>No games found. Create one!</Typography>
                ) : (
                    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', md: 'repeat(3, 1fr)' }, gap: 3 }}>
                        {games.map((game) => (
                            <Box key={game.id}>
                                <Card elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                                    <CardContent sx={{ flexGrow: 1 }}>
                                        <Typography variant="h6" component="div">
                                            {game.name}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            Players: {game.min_players} - {game.max_players}
                                        </Typography>
                                    </CardContent>
                                    <CardActions sx={{ display: 'flex', justifyContent: 'space-between' }}>
                                        <Box sx={{ display: 'flex', gap: 1 }}>
                                            <Button
                                                size="small"
                                                variant="contained"
                                                color="primary"
                                                component={RouterLink}
                                                to={`/play-game/${game.id}`}
                                            >
                                                Play
                                            </Button>
                                            <Button
                                                size="small"
                                                variant="outlined"
                                                color="secondary"
                                                component={RouterLink}
                                                to={`/edit-game/${game.id}`}
                                            >
                                                Edit
                                            </Button>
                                        </Box>
                                        <Button
                                            size="small"
                                            color="error"
                                            onClick={() => setDeleteGame(game)}
                                        >
                                            Delete
                                        </Button>
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
