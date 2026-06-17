# -*- coding: utf-8 -*-
import psutil
from loguru import logger
from models import ProcessInfo

def get_active_processes(sort_by: str = "cpu", search_query: str = "", limit: int = 15) -> list[ProcessInfo]:
    """
    Récupère la liste des processus système en cours d'exécution.
    Trie par le champ spécifié et applique un filtre de recherche.
    """
    processes = []
    
    # Récupération de tous les processus via psutil
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cpu_percent', 'memory_info', 'status', 'nice', 'exe', 'username']):
        try:
            pinfo = proc.info
            
            # Gestion des champs None ou manquants
            pid = pinfo.get('pid') or 0
            name = pinfo.get('name') or "Inconnu"
            cpu = pinfo.get('cpu_percent') or 0.0
            
            mem_info = pinfo.get('memory_info')
            mem_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
            
            status = pinfo.get('status') or "Unknown"
            nice = pinfo.get('nice')
            priority = str(nice) if nice is not None else "Normal"
            exe = pinfo.get('exe') or ""
            user = pinfo.get('username') or "System"

            # Filtrage par recherche
            if search_query:
                q = search_query.lower()
                if q not in name.lower() and q not in str(pid) and q not in user.lower():
                    continue

            processes.append(ProcessInfo(
                pid=pid,
                name=name,
                cpu_percent=cpu,
                memory_mb=mem_mb,
                status=status,
                priority=priority,
                exe_path=exe,
                user=user
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as e:
            logger.debug(f"Erreur de lecture du processus : {e}")
            continue

    # Tri des processus
    if sort_by == "cpu":
        processes.sort(key=lambda x: x.cpu_percent, reverse=True)
    elif sort_by == "mem":
        processes.sort(key=lambda x: x.memory_mb, reverse=True)
    elif sort_by == "name":
        processes.sort(key=lambda x: x.name.lower())
    elif sort_by == "pid":
        processes.sort(key=lambda x: x.pid)

    return processes[:limit]

def kill_process_by_pid(pid: int, force: bool = False) -> tuple[bool, str]:
    """
    Termine un processus par son PID.
    Envoie d'abord un SIGTERM (standard), puis un SIGKILL (force) si nécessaire.
    """
    try:
        proc = psutil.Process(pid)
        if force:
            proc.kill()  # Envoie un SIGKILL
            msg = f"Le processus {pid} a été forcé à s'arrêter (SIGKILL)."
        else:
            proc.terminate()  # Envoie un SIGTERM
            msg = f"Demande d'arrêt envoyée au processus {pid} (SIGTERM)."
        return True, msg
    except psutil.NoSuchProcess:
        return False, f"Le processus {pid} n'existe pas ou s'est déjà arrêté."
    except psutil.AccessDenied:
        return False, f"Permission refusée pour arrêter le processus {pid}. Droits insuffisants."
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du processus {pid} : {e}")
        return False, f"Erreur système : {str(e)}"

def change_process_priority(pid: int, priority_level: int) -> tuple[bool, str]:
    """
    Modifie la valeur 'nice' d'un processus pour changer sa priorité (nice de -20 à 19).
    Sur Windows, utilise les classes de priorité.
    """
    try:
        proc = psutil.Process(pid)
        # Sur Linux : nice value
        # Sur Windows : priority class
        import sys
        if sys.platform.startswith("win"):
            # Mapper la valeur de priorité à la classe Windows
            # 0: Normal, -10: High, 10: Idle
            import wmi
            # psutil gère aussi les classes de priorité sous Windows de manière simplifiée
            if priority_level < 0:
                proc.ionice(psutil.IOPRIO_HIGH)
            else:
                proc.ionice(psutil.IOPRIO_VERYLOW)
        else:
            # Linux nice : valeurs typiques [-20, 19]
            proc.nice(priority_level)
        return True, f"Priorité du processus {pid} modifiée avec succès."
    except psutil.NoSuchProcess:
        return False, f"Le processus {pid} n'existe pas."
    except psutil.AccessDenied:
        return False, f"Droits insuffisants pour changer la priorité du processus {pid}."
    except Exception as e:
        return False, f"Erreur : {str(e)}"
