# TODO: use osu-tools or rosu instead of akatsuki-pp-py
#       maybe add calculate_pp request too and finally use config.TOKEN?

from __future__ import annotations

import math
import re
import orjson
import subprocess
import os
import config

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypedDict, Iterable, Dict, Any, Tuple
from utils.logging import log, Ansi
from pathlib import Path

from refx_pp_py import Beatmap
from refx_pp_py import Calculator

from utils.OsuMapping import Mods, modstr2mod_dict


@dataclass
class ScoreParams:
    mode: int

    mods: int | None = None
    combo: int | None = None
    acc: float | None = None

    n300: int | None = None
    n100: int | None = None
    n50: int | None = None
    ngeki: int | None = None
    nkatu: int | None = None
    nmiss: int | None = None

    # NOTE: only for refx
    AC: int | None = None
    AR: float | None = None
    TW: int | None = None
    CS: bool | None = None
    HD: bool | None = None

class Performance(TypedDict):
    pp: float
    pp_acc: float | None
    pp_aim: float | None
    pp_speed: float | None
    pp_flashlight: float | None
    effective_miss_count: float | None
    pp_difficulty: float | None

class Difficulty(TypedDict):
    stars: float
    aim: float | None
    speed: float | None
    flashlight: float | None
    slider_factor: float | None
    speed_note_count: float | None
    stamina: float | None
    color: float | None
    rhythm: float | None
    peak: float | None

class PerformanceResult(TypedDict):
    performance: Performance
    difficulty: Difficulty

def calculate_performances(osu_file_path: str, scores: Iterable[ScoreParams]) -> list[PerformanceResult]:
    calc_ = Beatmap(path=osu_file_path)

    results: list[PerformanceResult] = []

    for score in scores:
        if score.acc and (
            score.n300 or score.n100 or score.n50 or score.ngeki or score.nkatu
        ):
            raise ValueError(
                "Must not specify accuracy AND 300/100/50/geki/katu. Only one or the other.",
            )

        if score.mods is not None:
            if score.mods & Mods.NIGHTCORE.value:
                score.mods |= Mods.DOUBLETIME.value

        calculator = Calculator(
            mode=score.mode % 4,
            mods=score.mods or 0,
            combo=score.combo,
            acc=score.acc,
            n300=score.n300,
            n100=score.n100,
            n50=score.n50,
            n_geki=score.ngeki,
            n_katu=score.nkatu,
            n_misses=score.nmiss,
            # NOTE: for refx
            shaymi_mode=True if score.mode > 3 else False
        )

        # NOTE: for refx
        if score.mode > 3:
            calculator.cheat_ac(0 if score.AC is None or score.AC < 1 else score.AC)
            calculator.cheat_arc(score.AR if score.AR is not None else 0)
            calculator.cheat_tw(int(150 if score.TW < 1 else score.TW))
            calculator.cheat_cs(bool(score.CS))
            calculator.cheat_hdr(bool(score.HD))
        else:
            calculator.cheat_ac(0 if score.AC is None or score.AC < 1 else score.AC)
            calculator.cheat_arc(score.AR if score.AR is not None else 0)
            calculator.cheat_hdr(bool(score.HD))

        result = calculator.performance(calc_)

        pp = result.pp

        if math.isnan(pp) or math.isinf(pp):
            pp = 0.0
        else:
            pp = round(pp, 3)

        results.append(
            {
                "performance": {
                    "pp": pp,
                    "pp_acc": result.pp_acc,
                    "pp_aim": result.pp_aim,
                    "pp_speed": result.pp_speed,
                    "pp_flashlight": result.pp_flashlight,
                    "effective_miss_count": result.effective_miss_count,
                    "pp_difficulty": result.pp_difficulty,
                },
                "difficulty": {
                    "stars": result.difficulty.stars,
                    "aim": result.difficulty.aim,
                    "speed": result.difficulty.speed,
                    "flashlight": result.difficulty.flashlight,
                    "slider_factor": result.difficulty.slider_factor,
                    "speed_note_count": result.difficulty.speed_note_count,
                    "stamina": result.difficulty.stamina,
                    "color": result.difficulty.color,
                    "rhythm": result.difficulty.rhythm,
                    "peak": result.difficulty.peak,
                },
            },
        )

    return results

# --- osu-tools ---
# NOTE: just an attempt, tee-hee
#       THIS IS VERY SLOW, DONT USE
#       shoulda used rosu-pp    
def verify_paths(osu_tools_path: str) -> bool:
    calculator_path = Path(osu_tools_path) / "PerformanceCalculator" / "bin" / "Release" / "net8.0" / "PerformanceCalculator.dll"
    
    # XXX: check if dotnet is installed
    try:
        subprocess.run(['dotnet', '--version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        log("dotnet is not installed or not in PATH", Ansi.YELLOW)
        return False
        
    if not calculator_path.exists():
        log(f"PerformanceCalculator not found at: {calculator_path}", Ansi.YELLOW)
        return False
        
    return True

def parse_performance_output(output: str) -> Tuple[float, Dict[str, float]]:
    """for simulate"""
    performance = {
        "star_rating": 0.0,
        "max_combo": 0.0
    }
    
    pp_value = 0.0

    patterns = {
        "pp": r"pp\s+:\s*([\d,]+\.?\d*)",
        "star_rating": r"star rating\s+:\s*([\d,]+\.?\d*)",
        "max_combo": r"max combo\s+:\s*([\d,]+\.?\d*)",
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, output)
        if match:
            value = match.group(1).replace(",", "")
            if key == "pp":
                pp_value = float(value)
            else:
                performance[key] = float(value)
    
    return pp_value, performance

def calculate_osu_tools(osu_file_path: str, scores: Iterable[ScoreParams], osu_tools_base_path: str = '../osutools') -> list[Dict[str, Any]]:
    """
    Calculate performance using osu-tools
    
    args:
        osu_file_path: path to the .osu file
        scores: iterable of ScoreParams objects
        osu_tools_base_path: base path to osu-tools directory
    
    returns:
        list of performance results
    """
    if not verify_paths(osu_tools_base_path):
        raise EnvironmentError("Required paths or executables not found")

    if not os.path.exists(osu_file_path):
        raise FileNotFoundError(f"Beatmap file not found: {osu_file_path}")

    calculator_path = os.path.join(
        osu_tools_base_path,
        "PerformanceCalculator/bin/Release/net8.0/PerformanceCalculator.dll"
    )
    
    results: list[Dict[str, Any]] = []

    # TODO: dont make the mode mapping here??
    mode_mapping = {
        0: "osu",
        1: "taiko",
        2: "catch",
        3: "mania"
    }

    for score in scores:
        try:
            cmd = [
                'dotnet',
                calculator_path,
                'simulate',
                mode_mapping.get(score.mode, 'osu'),
                osu_file_path
            ]
            
            if score.n50 is not None:
                cmd.extend(['-M', str(score.n50)])
            
            if score.mode == 3:
                if score.combo is not None:
                    cmd.extend(['-s', str(score.combo)])
            else:
                if score.combo is not None:
                    cmd.extend(['-c', str(score.combo)])
                if score.nmiss is not None:
                    cmd.extend(['-X', str(score.nmiss)])
            
            if score.mode not in [2, 3] and score.n100 is not None:
                cmd.extend(['-G', str(score.n100)])
            
            if score.acc is not None:
                cmd.extend(['-a', str(score.acc)])
            
            if score.mods is not None:
                for mod_str, mod_value in modstr2mod_dict.items():
                    # XXX: remove nc because dt is always active if nc is active
                    if score.mods & mod_value.value and mod_str not in {"NM", "V2", "NC"}:
                        cmd.extend(['-m', mod_str])
            
            try:
                calc_process = subprocess.run(
                    cmd,
                    text=True,
                    capture_output=True,
                    check=True
                )
                if config.DEBUG:
                    log(f"Running command: {' '.join(cmd)}")
                    log(f"Stdout: {calc_process.stdout}")
                
                if calc_process.stderr and config.DEBUG:
                    log(f"performance calculator stderr: {calc_process.stderr}")
                
                pp_value, performance_attrs = parse_performance_output(calc_process.stdout)
                
                results.append({
                    "performance": {
                        "pp": pp_value
                    },
                    "difficulty": {
                        "stars": performance_attrs["star_rating"],
                        "max_combo": performance_attrs["max_combo"]
                    },
                })
                
            except subprocess.CalledProcessError as e:
                log(f"command failed: {' '.join(e.cmd)}")
                log(f"return code: {e.returncode}")
                log(f"stdout: {e.stdout}")
                log(f"stderr: {e.stderr}")
                raise
                
        except Exception as e:
            log(f"error calculating performance for score: {e}", Ansi.RED)
            results.append({ # fallback
                "performance": {"pp": 0.0},
                "difficulty": {"stars": 0.0}
            })
    
    return results