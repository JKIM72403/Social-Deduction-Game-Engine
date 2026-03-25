import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { joinSession } from "../services/sessions";
import { useAuth } from "../contexts/AuthContext";

export default function LobbyLanding() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [joinCode, setJoinCode] = useState("");
  const [displayName, setDisplayName] = useState(user?.username ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleJoinLobby = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const snapshot = await joinSession(joinCode.trim().toUpperCase(), displayName.trim());
      navigate(`/sessions/${snapshot.session.id}`);
    } catch (err: any) {
      const message =
        err?.response?.data?.error ||
        "Unable to join that lobby right now. Double-check the code and try again.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ flexGrow: 1, display: "flex", alignItems: "center", justifyContent: "center", p: 4 }}>
      <Card sx={{ width: "100%", maxWidth: 860 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={4}>
            <Box>
              <Typography variant="h4" fontWeight={700} gutterBottom>
                Lobby Hub
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Join a live multiplayer session with a shareable code, or head back to the catalog to host a new lobby from any game template.
              </Typography>
            </Box>

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", md: "1.1fr 0.9fr" },
                gap: 3,
              }}
            >
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" fontWeight={600} gutterBottom>
                    Join an Existing Lobby
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Enter the code shared by the host. Your display name is what the other players will see in the lobby.
                  </Typography>

                  {error && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      {error}
                    </Alert>
                  )}

                  <Box component="form" onSubmit={handleJoinLobby}>
                    <TextField
                      fullWidth
                      label="Join Code"
                      value={joinCode}
                      onChange={(event) => setJoinCode(event.target.value.toUpperCase())}
                      inputProps={{ maxLength: 6 }}
                      sx={{ mb: 2 }}
                      required
                    />
                    <TextField
                      fullWidth
                      label="Display Name"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      sx={{ mb: 3 }}
                      required
                    />
                    <Button type="submit" variant="contained" size="large" disabled={submitting}>
                      {submitting ? "Joining..." : "Join Lobby"}
                    </Button>
                  </Box>
                </CardContent>
              </Card>

              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" fontWeight={600} gutterBottom>
                    Host a New Lobby
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    Hosting starts from the main template catalog. Pick a template, create a lobby, and the app will generate a shareable join code for your room automatically.
                  </Typography>

                  <Stack spacing={1.5} sx={{ mb: 3 }}>
                    <Typography variant="body2">1. Open the game catalog.</Typography>
                    <Typography variant="body2">2. Pick a template you want to host.</Typography>
                    <Typography variant="body2">3. Click `Host Lobby` to create a live session.</Typography>
                    <Typography variant="body2">4. Share the generated join code with your players.</Typography>
                  </Stack>

                  <Button variant="outlined" onClick={() => navigate("/")}>
                    Browse Templates
                  </Button>
                </CardContent>
              </Card>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
