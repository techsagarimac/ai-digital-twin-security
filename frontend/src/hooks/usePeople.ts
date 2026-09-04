import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { PersonLive } from "../types";

export function usePeople(pollMs = 4000) {
  const [people, setPeople] = useState<PersonLive[]>([]);
  useEffect(() => {
    let timer: number | undefined;
    const load = () => {
      api.people().then(setPeople).catch(() => undefined);
    };
    load();
    timer = window.setInterval(load, pollMs);
    return () => {
      if (timer) window.clearInterval(timer);
    };
  }, [pollMs]);
  return people;
}
