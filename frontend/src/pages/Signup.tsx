import { useState } from "react";
import { useNavigate, Navigate, Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import { useAuth } from "../contexts/AuthContext";
import bgImage from '../assets/mafia_bg.png';

export default function Signup() {
    const { user, signup } = useAuth();
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [passwordConfirm, setPasswordConfirm] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    if (user) return <Navigate to="/" />;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (password !== passwordConfirm) {
            setError("Passwords do not match.");
            return;
        }

        setSubmitting(true);
        try {
            await signup(username, email, password, passwordConfirm);
            navigate("/");
        } catch (err: any) {
            const data = err?.response?.data;
            const msg =
                data?.username?.[0] ||
                data?.password?.[0] ||
                data?.password_confirm?.[0] ||
                data?.non_field_errors?.[0] ||
                data?.error ||
                "Signup failed. Please try again.";
            setError(msg);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Box sx={{ 
            display: "flex", justifyContent: "center", alignItems: "center", height: "100%", p: 4,
            backgroundImage: `url(${bgImage})`, backgroundSize: 'cover', backgroundPosition: 'center', position: 'relative',
            '&::before': { content: '""', position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(10, 15, 25, 0.55)', zIndex: 0 }
        }}>
            <Card sx={{ 
                width: "100%", maxWidth: 420, position: 'relative', zIndex: 1,
                bgcolor: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(12px)',
                border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: 3,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)'
            }}>
                <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
                    <Typography variant="h5" fontWeight={600} gutterBottom>
                        Sign Up
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                        Create an account to build your own game templates.
                    </Typography>

                    {error && (
                        <Alert severity="error" sx={{ mb: 2 }}>
                            {error}
                        </Alert>
                    )}

                    <form onSubmit={handleSubmit}>
                        <TextField
                            fullWidth
                            label="Username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            sx={{ mb: 2 }}
                        />
                        <TextField
                            fullWidth
                            label="Email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            sx={{ mb: 2 }}
                        />
                        <TextField
                            fullWidth
                            label="Password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            inputProps={{ minLength: 8 }}
                            sx={{ mb: 2 }}
                        />
                        <TextField
                            fullWidth
                            label="Confirm Password"
                            type="password"
                            value={passwordConfirm}
                            onChange={(e) => setPasswordConfirm(e.target.value)}
                            required
                            sx={{ mb: 3 }}
                        />
                        <Button
                            type="submit"
                            variant="contained"
                            color="primary"
                            fullWidth
                            size="large"
                            disabled={submitting}
                        >
                            {submitting ? "Creating account..." : "Sign Up"}
                        </Button>
                    </form>

                    <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: "center" }}>
                        Already have an account?{" "}
                        <Typography
                            component={RouterLink}
                            to="/login"
                            variant="body2"
                            color="secondary.main"
                            sx={{ textDecoration: "none", fontWeight: 600 }}
                        >
                            Log In
                        </Typography>
                    </Typography>
                </CardContent>
            </Card>
        </Box>
    );
}
