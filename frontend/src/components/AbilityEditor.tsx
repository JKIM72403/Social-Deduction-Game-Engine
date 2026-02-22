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

interface Props {
    abilityId?: number;
    onSave: (ability: any) => void;
    onCancel: () => void;
    onDelete?: () => void;
}

export default function AbilityEditor({ abilityId, onSave, onCancel, onDelete }: Props) {
    const [ability, setAbility] = useState({
        name: "",
        ability_type: "KILL",
        phase: "NIGHT",
        description: "",
    });
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

    useEffect(() => {
        if (abilityId) {
            API.get(`/abilities/${abilityId}/`).then(res => {
                const data = res.data;
                setAbility({
                    name: data.name,
                    ability_type: data.ability_type,
                    phase: data.phase,
                    description: data.description || "",
                });
            });
        } else {
            setAbility({
                name: "",
                ability_type: "KILL",
                phase: "NIGHT",
                description: "",
            });
        }
    }, [abilityId]);

    const submit = async () => {
        try {
            let res;
            if (abilityId) {
                res = await API.put(`/abilities/${abilityId}/`, ability);
            } else {
                res = await API.post("/abilities/", ability);
            }
            onSave(res.data);
        } catch (e) {
            console.error(e);
            alert("Failed to save ability");
        }
    };

    const confirmDelete = async () => {
        if (!abilityId) return;
        try {
            await API.delete(`/abilities/${abilityId}/`);
            if (onDelete) onDelete();
        } catch (e) {
            console.error(e);
            alert("Failed to delete ability");
        } finally {
            setDeleteDialogOpen(false);
        }
    };

    return (
        <Box>
            <Typography variant="h6" sx={{ mb: 3 }}>
                {abilityId ? "Edit Ability" : "Create New Ability"}
            </Typography>

            <TextField
                fullWidth
                label="Ability Name"
                value={ability.name}
                onChange={e => setAbility({ ...ability, name: e.target.value })}
                sx={{ mb: 3 }}
            />

            <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Ability Type</InputLabel>
                <Select
                    value={ability.ability_type}
                    label="Ability Type"
                    onChange={e => setAbility({ ...ability, ability_type: e.target.value })}
                >
                    <MenuItem value="KILL">Kill Target</MenuItem>
                    <MenuItem value="PROTECT">Protect Target</MenuItem>
                    <MenuItem value="INVESTIGATE">Investigate Alignment</MenuItem>
                </Select>
            </FormControl>

            <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Phase</InputLabel>
                <Select
                    value={ability.phase}
                    label="Phase"
                    onChange={e => setAbility({ ...ability, phase: e.target.value })}
                >
                    <MenuItem value="NIGHT">Night</MenuItem>
                    <MenuItem value="DAY">Day</MenuItem>
                </Select>
            </FormControl>

            <TextField
                fullWidth
                multiline
                rows={3}
                label="Description"
                value={ability.description}
                onChange={e => setAbility({ ...ability, description: e.target.value })}
                sx={{ mb: 3 }}
            />

            <Box sx={{ display: 'flex', justifyContent: abilityId ? 'space-between' : 'flex-end', alignItems: 'center' }}>
                {abilityId && (
                    <Button onClick={() => setDeleteDialogOpen(true)} variant="outlined" color="error">
                        Delete
                    </Button>
                )}
                <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button onClick={onCancel} variant="outlined" color="secondary">
                        Cancel
                    </Button>
                    <Button onClick={submit} variant="contained" color="primary">
                        {abilityId ? "Update Ability" : "Save Ability"}
                    </Button>
                </Box>
            </Box>

            <Dialog
                open={deleteDialogOpen}
                onClose={() => setDeleteDialogOpen(false)}
            >
                <DialogTitle>Delete Ability?</DialogTitle>
                <DialogContent>
                    <DialogContentText>
                        Are you sure you want to permanently delete "{ability.name}"? This action cannot be undone.
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
