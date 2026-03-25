import { API } from "./api";
import type { SessionSnapshot } from "../types";

export async function createSession(templateId: number, displayName: string) {
  const response = await API.post<SessionSnapshot>("/sessions/", {
    template_id: templateId,
    display_name: displayName,
  });
  return response.data;
}

export async function joinSession(joinCode: string, displayName: string) {
  const response = await API.post<SessionSnapshot>("/sessions/join/", {
    join_code: joinCode,
    display_name: displayName,
  });
  return response.data;
}

export async function getSessionSnapshot(sessionId: number) {
  const response = await API.get<SessionSnapshot>(`/sessions/${sessionId}/snapshot/`);
  return response.data;
}

export async function setSessionReady(sessionId: number, isReady: boolean) {
  const response = await API.post<SessionSnapshot>(`/sessions/${sessionId}/ready/`, {
    is_ready: isReady,
  });
  return response.data;
}

export async function startSession(sessionId: number) {
  const response = await API.post<SessionSnapshot>(`/sessions/${sessionId}/start/`, {});
  return response.data;
}

export async function submitSessionVote(sessionId: number, targetParticipantId: number) {
  const response = await API.post<SessionSnapshot>(`/sessions/${sessionId}/actions/`, {
    action_type: "VOTE",
    target_participant_id: targetParticipantId,
  });
  return response.data;
}
