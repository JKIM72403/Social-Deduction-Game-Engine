import { useEffect, useState } from "react";
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutline';
import { API } from "../../services/api";
import type { GameData } from "../types";
import RoleEditor from "../../components/RoleEditor";
import { COLORS } from '../../constants/colors';

const selectedChipSx = {
    borderColor: COLORS.BORDER_HIGHLIGHT,
    borderWidth: 2,
    backgroundColor: 'rgba(34, 197, 94, 0.08)',
    '&:hover': {
        backgroundColor: 'rgba(34, 197, 94, 0.15)',
    },
};

const unselectedChipSx = {
    borderColor: COLORS.BORDER_DEFAULT,
    borderWidth: 1,
    '&:hover': {
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
};

interface Props {
    data: GameData;
    update: (data: Partial<GameData>) => void;
    onNext: () => void;
    onBack: () => void;
}

export default function Step2_Roles({ data, update, onNext, onBack }: Props) {
    const [availableRoles, setAvailableRoles] = useState<any[]>([]);
    const [isCreatingRole, setIsCreatingRole] = useState(false);

    useEffect(() => {
        loadRoles();
    }, []);

    const loadRoles = () => {
        API.get("/roles/").then(res => setAvailableRoles(res.data));
    };

    const addRoleToGame = (role: any) => {
        const existing = data.role_slots.find(s => s.roleId === role.id);
        if (existing) {
            update({
                role_slots: data.role_slots.map(s =>
                    s.roleId === role.id ? { ...s, count: s.count + 1 } : s
                )
            });
        } else {
            update({
                role_slots: [...data.role_slots, { roleId: role.id, roleName: role.name, count: 1 }]
            });
        }
    };

    const removeRoleFromGame = (roleId: number) => {
        update({
            role_slots: data.role_slots.filter(s => s.roleId !== roleId)
        });
    };

    const updateCount = (roleId: number, count: number) => {
        if (count <= 0) {
            removeRoleFromGame(roleId);
        } else {
            update({
                role_slots: data.role_slots.map(s =>
                    s.roleId === roleId ? { ...s, count } : s
                )
            });
        }
    };

    if (isCreatingRole) {
        return (
            <RoleEditor
                onSave={(newRole) => {
                    setAvailableRoles([...availableRoles, newRole]);
                    addRoleToGame(newRole);
                    setIsCreatingRole(false);
                }}
                onCancel={() => setIsCreatingRole(false)}
            />
        );
    }

    const totalRoles = data.role_slots.reduce((sum, s) => sum + s.count, 0);

    return (
        <div className="wizard-step">
            <Typography variant="h5" sx={{ mb: 3 }}>Manage Roles</Typography>

            <Box sx={{ display: 'flex', gap: 3 }}>
                {/* Available Roles */}
                <Box sx={{
                    flex: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    p: 2,
                }}>
                    <Typography variant="h6" sx={{ mb: 1 }}>Available Roles</Typography>
                    <Button
                        onClick={() => setIsCreatingRole(true)}
                        variant="outlined"
                        size="small"
                        sx={{ mb: 2 }}
                    >
                        + Create New Role
                    </Button>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {availableRoles.map(role => {
                            const isSelected = data.role_slots.some(s => s.roleId === role.id);
                            return (
                                <Chip
                                    key={role.id}
                                    label={`${role.name} (${role.alignment_name || 'Unknown'})`}
                                    variant="outlined"
                                    onClick={() => addRoleToGame(role)}
                                    sx={{
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                        ...(isSelected ? selectedChipSx : unselectedChipSx),
                                    }}
                                />
                            );
                        })}
                    </Box>
                </Box>

                {/* Selected Roles */}
                <Box sx={{
                    flex: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    p: 2,
                }}>
                    <Typography variant="h6" sx={{ mb: 1 }}>
                        Selected Roles ({totalRoles})
                    </Typography>
                    {data.role_slots.length === 0 ? (
                        <Typography variant="body2" color="text.secondary">
                            No roles selected.
                        </Typography>
                    ) : (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                            {data.role_slots.map(slot => (
                                <Chip
                                    key={slot.roleId}
                                    variant="outlined"
                                    onDelete={() => removeRoleFromGame(slot.roleId)}
                                    label={
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                            <span>{slot.roleName}</span>
                                            <IconButton
                                                size="small"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    updateCount(slot.roleId, slot.count - 1);
                                                }}
                                                sx={{ p: 0.25, color: 'text.secondary' }}
                                            >
                                                <RemoveCircleOutlineIcon sx={{ fontSize: 18 }} />
                                            </IconButton>
                                            <Typography variant="body2" component="span" sx={{ minWidth: 16, textAlign: 'center' }}>
                                                {slot.count}
                                            </Typography>
                                            <IconButton
                                                size="small"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    updateCount(slot.roleId, slot.count + 1);
                                                }}
                                                sx={{ p: 0.25, color: 'text.secondary' }}
                                            >
                                                <AddCircleOutlineIcon sx={{ fontSize: 18 }} />
                                            </IconButton>
                                        </Box>
                                    }
                                    sx={{
                                        cursor: 'default',
                                        transition: 'all 0.2s ease',
                                        ...selectedChipSx,
                                        '& .MuiChip-label': {
                                            display: 'flex',
                                            alignItems: 'center',
                                        },
                                    }}
                                />
                            ))}
                        </Box>
                    )}
                    {totalRoles < data.min_players && (
                        <Typography variant="body2" sx={{ color: COLORS.ERROR, mt: 1 }}>
                            Need at least {data.min_players} roles.
                        </Typography>
                    )}
                    {totalRoles > data.max_players && (
                        <Typography variant="body2" sx={{ color: COLORS.ERROR, mt: 1 }}>
                            Too many roles (max {data.max_players}).
                        </Typography>
                    )}
                </Box>
            </Box>

            <div className="actions">
                <Button onClick={onBack} variant="outlined" color="secondary">Back</Button>
                <Button
                    disabled={totalRoles < data.min_players || totalRoles > data.max_players}
                    onClick={onNext}
                    variant="contained"
                    color="primary"
                >
                    Next
                </Button>
            </div>
        </div>
    );
}
