import { useEffect, useState } from "react";
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import { API } from "../services/api";
import type { RoleTemplate, RoleSlot } from "../types";
import { COLORS } from '../constants/colors';

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

const alignmentColors = {
    TOWN: {
        color: COLORS.BORDER_BLUE,
        bgColor: 'rgba(59, 130, 246, 0.1)',
    },
    MAFIA: {
        color: COLORS.MAFIA,
        bgColor: 'rgba(239, 68, 68, 0.1)',
    },
    NEUTRAL: {
        color: COLORS.NEUTRAL,
        bgColor: 'rgba(234, 179, 8, 0.1)',
    },
};

interface Props {
    existingSlots: RoleSlot[];
    onSelectRole: (role: RoleTemplate) => void;
    onCreateCustomRole: () => void;
    onCancel: () => void;
}

export default function RoleSelector({ existingSlots, onSelectRole, onCreateCustomRole, onCancel }: Props) {
    const [availableRoles, setAvailableRoles] = useState<RoleTemplate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        API.get("/roles/")
            .then((res: { data: RoleTemplate[] }) => {
                setAvailableRoles(res.data);
                setLoading(false);
            })
            .catch((err: unknown) => {
                const errorMessage = err instanceof Error ? err.message : 'Failed to load roles';
                console.error("Failed to fetch roles", errorMessage);
                setError("Failed to load roles. Please try again.");
                setLoading(false);
            });
    }, []);

    const isRoleSelected = (roleId: number) => {
        return existingSlots.some(slot => slot.roleId === roleId);
    };

    const getRolesByAlignment = (alignment: 'TOWN' | 'MAFIA' | 'NEUTRAL') => {
        return availableRoles.filter((role: RoleTemplate) => role.alignment === alignment);
    };

    const townRoles = getRolesByAlignment('TOWN');
    const mafiaRoles = getRolesByAlignment('MAFIA');
    const neutralRoles = getRolesByAlignment('NEUTRAL');

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', p: 4 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ p: 3 }}>
                <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>
                <Button onClick={onCancel} variant="outlined" fullWidth>
                    Close
                </Button>
            </Box>
        );
    }

    const renderRoleSection = (title: string, roles: RoleTemplate[], alignment: 'TOWN' | 'MAFIA' | 'NEUTRAL') => {
        if (roles.length === 0) return null;

        const colors = alignmentColors[alignment];

        return (
            <Box sx={{ mb: 3 }}>
                <Typography 
                    variant="subtitle2" 
                    sx={{ 
                        mb: 1.5, 
                        fontWeight: 600,
                        color: colors.color,
                        textTransform: 'uppercase',
                        fontSize: '0.75rem',
                        letterSpacing: '0.05em'
                    }}
                >
                    {title}
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {roles.map(role => {
                        const isSelected = isRoleSelected(role.id);
                        return (
                            <Chip
                                key={role.id}
                                label={role.name}
                                variant="outlined"
                                onClick={() => onSelectRole(role)}
                                sx={{
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease',
                                    ...(isSelected ? selectedChipSx : {
                                        ...unselectedChipSx,
                                        borderColor: colors.color,
                                        backgroundColor: colors.bgColor,
                                        '&:hover': {
                                            backgroundColor: colors.bgColor,
                                            opacity: 0.8,
                                        },
                                    }),
                                }}
                            />
                        );
                    })}
                </Box>
            </Box>
        );
    };

    return (
        <Box>
            <Typography variant="h6" sx={{ mb: 3 }}>
                Add Role to Game
            </Typography>

            <Button
                onClick={onCreateCustomRole}
                variant="outlined"
                fullWidth
                sx={{ mb: 3 }}
            >
                + Create Custom Role
            </Button>

            {renderRoleSection('Town Roles', townRoles, 'TOWN')}
            {renderRoleSection('Mafia Roles', mafiaRoles, 'MAFIA')}
            {renderRoleSection('Neutral Roles', neutralRoles, 'NEUTRAL')}

            {availableRoles.length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', my: 4 }}>
                    No roles available. Create a custom role to get started.
                </Typography>
            )}

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 3 }}>
                <Button onClick={onCancel} variant="outlined" color="secondary">
                    Cancel
                </Button>
            </Box>
        </Box>
    );
}
