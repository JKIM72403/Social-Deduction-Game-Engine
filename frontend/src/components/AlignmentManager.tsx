import { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import IconButton from '@mui/material/IconButton';
import DeleteIcon from '@mui/icons-material/Delete';
import { API } from '../services/api';
import type { Alignment } from '../types';

interface AlignmentManagerProps {
    gameId?: number;
    onCancel: () => void;
}

const AlignmentManager = ({ gameId, onCancel }: AlignmentManagerProps) => {
    const [alignments, setAlignments] = useState<Alignment[]>([]);
    const [newName, setNewName] = useState('');
    const [loading, setLoading] = useState(false);

    const fetchAlignments = async () => {
        try {
            const params = gameId ? { game_template: gameId } : undefined;
            const res = await API.get('/alignments/', { params });
            setAlignments(res.data);
        } catch (e) {
            console.error('Failed to fetch alignments', e);
        }
    };

    useEffect(() => {
        fetchAlignments();
    }, [gameId]);

    const handleCreate = async () => {
        if (!newName.trim()) return;
        setLoading(true);
        try {
            await API.post('/alignments/', { name: newName.trim(), game_template: gameId });
            setNewName('');
            fetchAlignments();
        } catch (e) {
            console.error('Failed to create alignment', e);
            alert('Failed to create alignment. Make sure the name is unique.');
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!window.confirm('Are you sure you want to delete this alignment? Deletion is blocked while any role or win condition still uses it.')) return;
        try {
            await API.delete(`/alignments/${id}/`);
            fetchAlignments();
        } catch (e) {
            console.error('Failed to delete alignment', e);
            alert('Failed to delete alignment. Remove any roles or win conditions using it first.');
        }
    };

    return (
        <Box>
            <Typography variant="h6" sx={{ mb: 3 }}>Custom Alignments</Typography>
            {!gameId && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Save this game once before adding custom alignments. That keeps them tied to this game only.
                </Typography>
            )}
            
            <Box sx={{ display: 'flex', gap: 1, mb: 4 }}>
                <TextField
                    fullWidth
                    size="small"
                    label="New Alignment Name"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    disabled={loading || !gameId}
                />
                <Button 
                    variant="contained" 
                    onClick={handleCreate}
                    disabled={loading || !newName.trim() || !gameId}
                >
                    Add
                </Button>
            </Box>

            <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                Existing Alignments
            </Typography>
            <List dense sx={{ 
                border: '1px solid', 
                borderColor: 'divider', 
                borderRadius: 1,
                bgcolor: 'background.paper',
                maxHeight: 300,
                overflowY: 'auto'
            }}>
                {alignments.map((a) => (
                    <ListItem 
                        key={a.id}
                        secondaryAction={
                            !a.is_default && (
                                <IconButton edge="end" size="small" onClick={() => handleDelete(a.id)}>
                                    <DeleteIcon fontSize="small" />
                                </IconButton>
                            )
                        }
                    >
                        <ListItemText 
                            primary={a.name} 
                            secondary={a.is_default ? 'Default (cannot delete)' : 'Custom'}
                        />
                    </ListItem>
                ))}
                {alignments.length === 0 && (
                    <ListItem>
                        <ListItemText primary="No alignments found" />
                    </ListItem>
                )}
            </List>

            <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
                <Button onClick={onCancel} variant="outlined">
                    Close
                </Button>
            </Box>
        </Box>
    );
};

export default AlignmentManager;
