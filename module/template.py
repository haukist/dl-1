from collections import defaultdict
from functools import reduce

from core.log import log
from core.timeline import now
from core.advbase import Adv
from core.modifier import Selfbuff

class StanceAdv(Adv):
    def config_stances(self, stance_dict, default_stance=None, hit_threshold=0, deferred=True):
        """@param: stance_dict[str] -> ModeManager or None"""
        if default_stance is None:
            default_stance = next(iter(stance_dict))
        self.stance = default_stance
        self.hit_threshold = hit_threshold
        self.next_stance = default_stance
        self.stance_dict = stance_dict
        self.has_alt_x = False
        for name, mode in self.stance_dict.items():
            if mode:
                self.has_alt_x = self.has_alt_x or 'x' in mode.alt
                try:
                    mode.alt['x'].deferred = deferred
                except KeyError:
                    pass
            setattr(self, name, lambda: self.queue_stance(name))
        self.update_stance()

    def update_stance(self):
        if self.next_stance is not None:
            log('stance', self.next_stance)
            curr_stance = self.stance_dict[self.stance]
            next_stance = self.stance_dict[self.next_stance]
            if curr_stance is not None:
                curr_stance.off()
            if next_stance is not None:
                if self.can_change_combo():
                    next_stance.on()
                else:
                    next_stance.on_except('x')
            self.stance = self.next_stance
            self.next_stance = None

    def queue_stance(self, stance):
        if self.can_queue_stance(stance):
            self.next_stance = stance
            self.update_stance()
            return True
        try:
            self.stance_dict[stance].alt['x'].on()
        except KeyError:
            pass
        return False

    def can_queue_stance(self, stance):
        return (
            stance not in (self.stance, self.next_stance) and 
            not self.Skill._static.silence == 1
        )
    
    def can_change_combo(self):
        return self.has_alt_x and self.hits >= self.hit_threshold

    def s(self, n, stance=None):
        if stance:
            self.queue_stance(stance)
        return super().s(n)


class RngCritAdv(Adv):

    def config_rngcrit(self, cd=0, ev=None, ev_len=None):
        self.rngcrit_cd = False
        self.rngcrit_cd_duration = cd
        if ev:
            self.effect_duration = ev
            self.crit_mod = self.ev_custom_crit_mod
            self.rngcrit_state_len = ev_len or (self.effect_duration // self.rngcrit_cd_duration) + 1
            self.rngcrit_states = {(None,)*self.rngcrit_state_len: 1.0}
            self.prev_log_time = 0
        else:
            self.crit_mod = self.rand_custom_crit_mod
        if cd > 0:
            self.rngcrit_t = self.Timer(self.rngcrit_cd_off, self.rngcrit_cd_duration)

    def rngcrit_skip(self):
        return False

    def rngcrit_cb(self, mrate=None):
        raise NotImplementedError('Implement rngcrit_cb')

    def rngcrit_cd_off(self, t=None):
        self.rngcrit_cd = False

    def ev_custom_crit_mod(self, name):
        if name == 'test':
            return self.solid_crit_mod(name)
        else:
            chance, cdmg = self.combine_crit_mods()
            t = now()
            
            new_states = defaultdict(lambda: 0.0)
            for state, state_p in self.rngcrit_states.items():
                if self.effect_duration > 0:
                    state = tuple([b if b is not None and t - b <= self.effect_duration else None for b in state])
                if state[0] is not None and t - state[0] < self.rngcrit_cd_duration:
                    new_states[state] += state_p
                else:
                    miss_rate = 1.0 - chance
                    new_states[state] += miss_rate * state_p
                    for i in range(self.rngcrit_state_len):
                        # t is the newest buff timing so it's in the front; the rest remain in order
                        new_states[(t,) + state[0:i] + state[i + 1:]] += chance * state_p / self.rngcrit_state_len
            mrate = reduce(lambda mv, s: mv + (sum(int(b is not None) for b in s[0]) * s[1]), new_states.items(), 0)
            if self.prev_log_time == 0 or self.prev_log_time < t - self.rngcrit_cd_duration:
                log('rngcrit', mrate)
                self.prev_log_time = t
            self.rngcrit_cb(mrate)
            self.rngcrit_states = new_states

            return chance * (cdmg - 1) + 1

    def rand_custom_crit_mod(self, name):
        if self.rngcrit_cd or name == 'test' or self.rngcrit_skip():
            return self.solid_crit_mod(name)
        else:
            crit = self.rand_crit_mod(name)
            if crit > 1:
                self.rngcrit_cb()
                if self.rngcrit_cd_duration > 0:
                    self.rngcrit_cd = True
                    self.rngcrit_t.on()
            return crit

