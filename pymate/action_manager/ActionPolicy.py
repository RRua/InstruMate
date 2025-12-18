from abc import abstractmethod
from pymate.action_manager.graph.Action import ActionBag
from pymate.action_manager.graph.GraphManager import GraphManager
from pymate.action_manager.ActionMemory import MemoryManager
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


class PolicyInfo:

    def __init__(self, policy_name: str, task: str = None, success=False, policy_data:dict = None):
        self.policy_name = policy_name
        self.task = task
        self.success = success
        self.policy_data = policy_data if policy_data is not None else {}

    def to_dict(self):
        return {
            "policy_name": self.policy_name,
            "task": self.task,
            "success": self.success,
            "data": self.policy_data
        }


class ActionPolicy:

    @abstractmethod
    def choose_actions(self, task: str, memory_manager: MemoryManager, graph_manager: GraphManager) -> tuple[
            ActionBag, PolicyInfo]:
        raise NotImplementedError()


def show_images_and_ask_user(states_dir, img):
    import os
    resize_factor = 4
    root = tk.Tk()
    root.title("Image Comparison")
    base_states_dir = os.path.basename(states_dir)
    actual_snapshot_file = os.path.join(states_dir, img)
    image = Image.open(actual_snapshot_file)
    width, height = image.size
    image = image.resize((int(width / resize_factor), int(height / resize_factor)))
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(root, image=photo)
    label.image = photo
    label.pack(side=tk.LEFT)
    root.update()
    response = messagebox.askyesno("Question", "By the last screen, did you take any action?")
    result = False
    if response:
        result = True
    root.destroy()
    return result


class ManualPolicy(ActionPolicy):
    def __init__(self):
        super().__init__()

    def choose_actions(self, task: str, memory_manager: MemoryManager, graph_manager: GraphManager) -> tuple[
            ActionBag, PolicyInfo]:
        while True:
            root = tk.Tk()
            root.withdraw()
            messagebox.askokcancel("Confirm", f"Your task is: {task}. Interact with the device and press any key when finished")
            root.destroy()
            img = graph_manager.get_current_state_snapshot()
            response = show_images_and_ask_user(graph_manager.states_dir, img)
            if response:
                succeeded = True
            else:
                succeeded = False
            action_bag = ActionBag()
            policy_info = PolicyInfo(policy_name=ManualPolicy.__name__, task=task, success=succeeded, policy_data={})
            return action_bag, policy_info


if __name__ == "__main__":
    res = show_images_and_ask_user(
        'I:\\git\\forensicmate-static-analysis\\output\\MONITOR\\com.whatsapp-2.24.4.76\\states\\ViewState_0fcf1789e4acdcdf55f7af86e14ef22b_Snapshot.png')
    print(res)
