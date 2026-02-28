import { useEffect, useState } from "react";
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import { API } from "../services/api";
import type { Phase } from "../types";

interface Props {
    gameId?: number;
    phaseId?: number;
    initialData?: Phase;
    onSave: (phase: Phase) => void;
    onCancel: () => void;
    onDelete?: () => void;
}

export default function PhaseEditor({ gameId, phaseId, initialData, onSave, onCancel, onDelete }: Props) {
    const [phase, setPhase] = useState<Phase>(initialData || {
        name: "",
        phase_type: "NIGHT",
        order: 0
    });
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

    useEffect(() => {
        if (initialData) {
            setPhase(initialData);
        } else if (phaseId) {
            API.get(`/phases/${phaseId}/`).then(res => {
                setPhase(res.data);
            });
        }
    }, [phaseId, initialData]);

    const submit = async () => {
        if (!gameId) {
            // Local-only save for new games
            onSave(phase);
            return;
        }

        try {
            let res;
            const payload = { ...phase, game_template: gameId };
            if (phaseId) {
                res = await API.put(`/phases/${phaseId}/`, payload);
            } else {
                res = await API.post("/phases/", payload);
            }
            onSave(res.data);
        } catch (e) {
            console.error(e);
            alert("Failed to save phase");
        }
    };

    const confirmDelete = async () => {
        if (!gameId) {
            if (onDelete) onDelete();
            return;
        }

        if (!phaseId) {
            if (onDelete) onDelete();
            return;
        }

        try {
            await API.delete(`/phases/${phaseId}/`);
            if (onDelete) onDelete();
        } catch (e) {
            console.error(e);
            alert("Failed to delete phase");
        } finally {
            setDeleteDialogOpen(false);
        }
    };

    return (
        <Box>
            <Typography variant="h6" sx={{ mb: 3 }}>
                {(phaseId || initialData) ? "Edit Phase" : "Create New Phase"}
            </Typography>

            <TextField
                fullWidth
                label="Phase Name"
                value={phase.name}
                placeholder="e.g., Night, Day, Dusk"
                onChange={e => setPhase({ ...phase, name: e.target.value })}
                sx={{ mb: 3 }}
            />

            <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Phase Type</InputLabel>
                <Select
                    value={phase.phase_type}
                    label="Phase Type"
                    onChange={e => setPhase({ ...phase, phase_type: e.target.value as any })}
                >
                    <MenuItem value="NIGHT">Night (Abilities enabled)</MenuItem>
                    <MenuItem value="DAY">Day (Discussion focus)</MenuItem>
                    <MenuItem value="VOTING">Voting (Execution focus)</MenuItem>
                </Select>
            </FormControl>


            <Box sx={{ display: 'flex', justifyContent: (phaseId || initialData) ? 'space-between' : 'flex-end', alignItems: 'center' }}>
                {(phaseId || initialData) && (
                    <Button onClick={() => setDeleteDialogOpen(true)} variant="outlined" color="error">
                        Delete
                    </Button>
                )}
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button onClick={onCancel} variant="outlined" color="secondary">
                        Cancel
                    </Button>
                    <Button onClick={submit} variant="contained" color="primary">
                        {(phaseId || initialData) ? "Update Phase" : "Save Phase"}
                    </Button>
                </Box>
            </Box>

            <Dialog
                open={deleteDialogOpen}
                onClose={() => setDeleteDialogOpen(false)}
            >
                <DialogTitle>Delete Phase?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Are you sure you want to permanently delete "{phase.name}"? This action cannot be undone.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteDialogOpen(false)} color="secondary">Cancel</Button>
                    <Button onClick={confirmDelete} color="error" variant="contained">Delete</Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
}
