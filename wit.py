from datetime import datetime
from distutils.dir_util import copy_tree
from distutils.errors import DistutilsFileError
import filecmp
import os
from pathlib import Path, PurePath
import random
import shutil
import sys
import types

from graphviz import Digraph


COMMIT_ID_GEN = "1234567890abcdef"


class Wit:
    def __init__(self, wit_dir):
        self.dir = wit_dir
        self.witdir = os.path.join(self.dir, ".wit")
        self.staging_area = os.path.join(self.dir, ".wit/staging_area")
        self.images = os.path.join(self.dir, ".wit/images")
        self.rel_staging_area = ".wit/staging_area"
        self.rel_images = ".wit/images" 
         
    def activate(self, branch):
        with open(os.path.join(self.witdir, 'activated.txt'), 'w') as branch_file:
            branch_file.write(branch)
    
    def get_branch(self):
        with open(os.path.join(self.witdir, 'activated.txt')) as branch_file:
            return branch_file.read()

    def isbranch(self, id):
        with open(os.path.join(self.witdir, 'references.txt')) as ref:
            lines = ref.read().splitlines()
        for line in lines:
            if line[:line.index('=')] == id:
                return True
        return False

    def get_id_from_branch(self, name):
        with open(os.path.join(self.witdir, 'references.txt')) as ref:
            file_content = ref.read()
        try:
            location = file_content.index(name)
        except ValueError:
            print("Branch not found")
            return
        file_content = file_content[location:]
        return file_content[file_content.index('=') + 1: file_content.index('\n')]

    def update_branch(self, name, new_commit):
        with open(os.path.join(self.witdir, 'references.txt')) as ref:
            ref_content = ref.readlines()
        branch_found = False
        for index, line in enumerate(ref_content):
            if name in line:
                ref_content[index] = f"{name}={new_commit}\n"
                branch_found = True
                break
        if not branch_found:
            raise ValueError(f"Branch {name} not found.")
        with open(os.path.join(self.witdir, 'references.txt'), 'w') as ref:
            ref.write(''.join(ref_content))

    def get_changed_files(self, f1, f2):
        changed_files = []
        for dirpath, _, _ in os.walk(f1):
            in_f2 = os.path.join(f2, os.path.relpath(dirpath, f1))
            diff = filecmp.dircmp(in_f2, dirpath).diff_files
            if diff:
                changed_files.extend(os.path.join(dirpath, file) for file in diff)
        return changed_files

    def get_untracked_files(self):
        untracked_files = []
        for dirpath, dirnames, filenames in os.walk(self.dir, topdown=True):
            dirnames[:] = [d for d in dirnames if d != '.wit']
            for filename in filenames:
                rel_file_path = os.path.relpath(os.path.join(dirpath, filename), self.dir)
                possible_untracked_file = os.path.join(self.staging_area, rel_file_path)
                if not os.path.exists(possible_untracked_file):
                    untracked_files.append(possible_untracked_file)
        return untracked_files

    def get_head(self):
        with open(os.path.join(self.witdir, 'references.txt')) as ref:
            head, *_ = ref.read().splitlines()
        head = head[head.index('=') + 1:]
        return head

    def get_uncommited_files(self, commit_id):
        to_commit = []
        commited_dir = os.path.join(self.images, commit_id)
        for dirpath, _, filenames in os.walk(self.staging_area):
            for filename in filenames:
                rel_file_path = os.path.relpath(os.path.join(dirpath, filename), self.staging_area)  
                possible_uncommited_file = os.path.join(commited_dir, rel_file_path)
                if not os.path.exists(possible_uncommited_file):
                    to_commit.append(possible_uncommited_file)
        return to_commit

    def update_head(self, new_head):
        with open(os.path.join(self.witdir, 'references.txt')) as ref_file:
            _, *rest = ref_file.readlines()
        with open(os.path.join(self.witdir, 'references.txt'), 'w') as ref_file:
            ref_file.write(f"HEAD={new_head}\n" + ''.join(rest))

    def update_master(self, new_master):
        with open(os.path.join(self.witdir, 'references.txt')) as ref:
            head, _, *rest = ref.readlines()
        with open(os.path.join(self.witdir, 'references.txt'), 'w') as ref:
            ref.write(head + f"master={new_master}\n" + ''.join(rest))

    def get_parent(self, commit_id):
        with open(os.path.join(self.images, f"{commit_id}.txt")) as metadata_file:
            parent, *_ = metadata_file.read().splitlines()
        parent = parent[parent.index('=') + 1:]
        return parent

    def get_parents(self, commit_id):
        parents = []
        parents.append(commit_id)
        parent = self.get_parent(commit_id)
        if parent:
            parents.extend(self.get_parents(parent))
            return parents
        else:
            return parents

    
class WitNotFoundError(Exception):
    def __str__(self):
        return "No wit folder found in parent directories"


def iswit(dir):
    """Returns path to .wit dir, if one found in parent directories
    or empty string if no .wit dir found."""
    if os.path.isfile(dir):
        return iswit(os.path.dirname(dir))
    if '.wit' in os.listdir(dir):
        return Wit(dir)
    elif not os.path.basename(dir):
        raise WitNotFoundError
    else:
        return iswit(os.path.dirname(dir))


def init():
    os.makedirs(".wit/images")
    os.mkdir(".wit/staging_area")
    with open('.wit/activated.txt', 'w') as branch_file:
        branch_file.write('master')
    with open('.wit/references.txt', 'w') as ref_file:
            ref_file.write("HEAD=\nmaster=\nbranch=\n")


def add(thing):
    if not os.path.exists(thing):
        raise FileNotFoundError
    init_wd = os.getcwd()
    chain = thing
    if os.path.isfile(thing):
        chain = os.path.dirname(thing)
    while '.wit' not in os.listdir(os.getcwd()):
        chain = os.path.join(os.path.basename(os.getcwd()), chain)
        os.chdir('..')
        current_dir = os.path.basename(os.getcwd())
        if not current_dir:
            raise WitNotFoundError     
    if chain:
        try:
            os.makedirs(os.path.join(os.getcwd(), '.wit/staging_area', chain))
        except FileExistsError:
            pass
    try:
        copy_tree(os.path.join(init_wd, thing), os.path.join(os.getcwd(), '.wit/staging_area', chain))
    except DistutilsFileError:
        #thing is file
        shutil.copy(os.path.join(init_wd, thing), os.path.join(os.getcwd(), '.wit/staging_area', chain))


def commit(message):
    wit = iswit(os.getcwd())
    commit_id = ''.join(random.choices(COMMIT_ID_GEN, k=40))
    commit_dir = os.path.join(wit.images, commit_id)
    current_time = datetime.utcnow().strftime("%c %z")
    parent = wit.get_head()
    if not wit.get_uncommited_files(parent):
        print("No changes have been made since last commit")
        return
    os.mkdir(commit_dir)
    with open(os.path.join(wit.images, f"{commit_id}.txt"), 'w') as metadata_file:
        metadata_file.write(
            f"parent={parent}\n"
            f"{current_time}\n"
            f"message={message}\n"
        )
    copy_tree(wit.staging_area, commit_dir)
    active = wit.get_branch()
    if wit.get_head() == wit.get_id_from_branch(active):
        wit.update_branch(active, commit_id)
    wit.update_head(commit_id)


def status(prnt_stat=False):
    wit = iswit(os.getcwd())
    commit_id = wit.get_head()
    to_commit = wit.get_uncommited_files(commit_id)
    to_stage = wit.get_changed_files(f1=wit.staging_area, f2=wit.dir)
    untracked = wit.get_untracked_files()
    if prnt_stat:
        print(
            f"commit_id: {commit_id}\n"
            f"Changes to be committed: {to_commit}\n"
            f"Changes not staged for commit: {to_stage}\n"
            f"Untracked files: {untracked}"
        )
    return commit_id, to_commit, to_stage, untracked


def rm(path):
    abs_path = os.path.abspath(path)
    wit = iswit(abs_path)
    rel_to_staging = os.path.relpath(abs_path, wit.staging_area)
    os.remove(os.path.join(wit.dir, rel_to_staging))
    os.remove(abs_path)


def checkout(commit_id):
    wit = iswit(os.getcwd())
    if wit.isbranch(commit_id):
        with open(os.path.join(wit.witdir, 'activated.txt'), 'w') as branch_file:
            branch_file.write(commit_id)
        commit_id = wit.get_id_from_branch(commit_id)
    src = os.path.join(wit.images, commit_id)
    _, to_commit, to_stage, _ = status()
    if to_commit or to_stage:
        print("Uncommited/unstaged changes. checkout cancelled.")
        return
    copy_tree(os.path.join(src, '.'), wit.dir)
    if wit.get_branch() == 'master' and wit.get_id_from_branch('master') == wit.get_head():
        wit.update_master(commit_id)
    wit.update_head(commit_id)


def generate_edges(num_of_nodes, graff):
    for i in range(1, num_of_nodes):
        graff.edge(str(i), str(i + 1))


def graph():
    wit = iswit(os.getcwd())
    parent = "None"
    with open(os.path.join(wit.witdir, 'references.txt')) as ref:
        head = ref.read().splitlines()[0]
        head = head[head.index('=') + 1:]
    parent = head
    counter, graff = 0, Digraph('Parenthood', filename='parenthood', format='png')
    while parent:
        #graff.edge(str(counter), parent)
        with open(os.path.join(wit.images, f'{parent}.txt')) as metadata:
            counter += 1
            next_parent = metadata.read().splitlines()[0]
            next_parent = next_parent[next_parent.index('=') + 1:]
            graff.edge(parent, next_parent)
            parent = next_parent
    #generate_edges(counter, graff)
    graff.view()


def branch(name):
    wit = iswit(os.getcwd())
    with open(os.path.join(wit.witdir, 'references.txt'), 'a') as ref:
        ref.write(f"{name}={wit.get_head()}\n")


def merge(name):
    wit = iswit(os.getcwd())
    _, stat, _, _ = status()
    if stat:
        print("Changes need to be commited")
        return
    branch_id = wit.get_id_from_branch(name)
    head_parents = wit.get_parents(wit.get_head())
    branch_parents = wit.get_parents(branch_id)
    common_parent = ''
    for parent in head_parents:
        if parent in branch_parents:
            common_parent = parent
    if not common_parent:
        raise ValueError
    #common_parent = set(head_parents) | set(branch_parents)
    #common_parent = common_parent[0]
    changed_files = wit.get_changed_files(os.path.join(wit.images, common_parent), os.path.join(wit.images, branch_id))
    for file in changed_files:
        rel_path = os.path.relpath(file , os.path.join(wit.images, branch_id))
        new_path = os.path.join(wit.staging_area, os.path.dirname(rel_path))
        os.mkdir(new_path)
        shutil.copy(file, new_path)
    commit("merge")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        current_module = sys.modules['__main__']
        function, *args = sys.argv[1:]
        getattr(current_module, function)(*args) 