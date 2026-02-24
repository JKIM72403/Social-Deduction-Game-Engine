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

export default function Login() {
    const { user, login } = useAuth();
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    if (user) return <Navigate to="/" />;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSubmitting(true);
        try {
            await login(username, password);
            navigate("/");
        } catch (err: any) {
            const msg =
                err?.response?.data?.error ||
                err?.response?.data?.non_field_errors?.[0] ||
                "Login failed. Please try again.";
            setError(msg);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", flexGrow: 1, p: 4 }}>
            <Card sx={{ width: "100%", maxWidth: 420 }}>
                <CardContent sx={{ p: 4 }}>
                    <Typography variant="h5" fontWeight={600} gutterBottom>
                        Log In
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                        Enter your credentials to continue.
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
                            label="Password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
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
                            {submitting ? "Logging in..." : "Log In"}
                        </Button>
                    </form>

                    <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: "center" }}>
                        Don't have an account?{" "}
                        <Typography
                            component={RouterLink}
                            to="/signup"
                            variant="body2"
                            color="secondary.main"
                            sx={{ textDecoration: "none", fontWeight: 600 }}
                        >
                            Sign Up
                        </Typography>
                    </Typography>
                </CardContent>
            </Card>
        </Box>
    );
}
