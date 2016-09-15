#
# Copyright (c) 2014-2016 ISPRAS (http://www.ispras.ru)
# Institute for System Programming of the Russian Academy of Sciences
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import re
import json
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from bridge.utils import ArchiveFileContent
from reports.models import ReportUnsafe


TAB_LENGTH = 4
SOURCE_CLASSES = {
    'comment': "ETVComment",
    'number': "ETVNumber",
    'line': "ETVSrcL",
    'text': "ETVText",
    'key1': "ETVKey1",
    'key2': "ETVKey2"
}

KEY1_WORDS = [
    '#ifndef', '#elif', '#undef', '#ifdef', '#include', '#else', '#define',
    '#if', '#pragma', '#error', '#endif', '#line'
]

KEY2_WORDS = [
    '__based', 'static', 'if', 'sizeof', 'double', 'typedef', 'unsigned', 'new', 'this', 'break', 'inline', 'explicit',
    'template', 'bool', 'for', 'private', 'default', 'else', 'const', '__pascal', 'delete', 'switch', 'continue', 'do',
    '__fastcall', 'union', 'extern', '__cdecl', 'friend', '__inline', 'int', '__virtual_inheritance', 'void', 'case',
    '__multiple_inheritance', 'enum', 'short', 'operator', '__asm', 'float', 'struct', 'cout', 'public', 'auto', 'long',
    'goto', '__single_inheritance', 'volatile', 'throw', 'namespace', 'protected', 'virtual', 'return', 'signed',
    'register', 'while', 'try', 'char', 'catch', 'cerr', 'cin'
]


def get_error_paths(data):
    err_paths = [[], []]
    must_have_thread = False
    curr_node = data['violation nodes'][0]
    if not isinstance(data['nodes'][curr_node][0], int):
        raise ValueError('Error traces with one path are supported')
    while curr_node != data['entry node']:
        if not isinstance(data['nodes'][curr_node][0], int):
            raise ValueError('Error traces with one path are supported')
        curr_in_edge = data['edges'][data['nodes'][curr_node][0]]
        if 'thread' in curr_in_edge:
            must_have_thread = True
            err_paths[int(curr_in_edge['thread'])].insert(0, data['nodes'][curr_node][0])
        elif must_have_thread:
            raise ValueError("All error trace edges must have thread identifier ('0' or '1')")
        else:
            err_paths[0].insert(0, data['nodes'][curr_node][0])
        curr_node = curr_in_edge['source node']
    if len(err_paths[0]) == 0:
        del err_paths[0]
    if len(err_paths[1]) == 0:
        del err_paths[1]
    return err_paths


class GetETV(object):
    def __init__(self, error_trace, include_assumptions=True):
        self.include_assumptions = include_assumptions
        self.html_traces = []
        self.assumes = []
        self.data = json.loads(error_trace)
        self.traces = get_error_paths(self.data)
        for trace in self.traces:
            self.__html_trace(trace)
        self.attributes = []

    def __get_attributes(self):
        # TODO: return list of error trace attributes like [<attr name>, <attr value>]. Ignore 'programfile'.
        pass

    def __html_trace(self, trace):
        lines_data = []

        cnt = 0
        file = None
        has_main = False
        curr_offset = 1
        max_line_length = 1
        scope_stack = ['global']
        assume_scopes = {'global': []}
        scopes_to_show = []
        scopes_to_hide = []

        def add_fake_line(fake_code):
            lines_data.append({
                'code': fake_code,
                'line': None,
                'offset': curr_offset * ' ',
                'class': scope_stack[-1],
                'hide_id': None
            })

        def fill_assumptions(current_assumptions=None):
            assumptions = []
            if scope_stack[-1] in assume_scopes:
                for j in range(0, len(assume_scopes[scope_stack[-1]])):
                    assume_id = '%s_%s' % (scope_stack[-1], j)
                    if isinstance(current_assumptions, list) and assume_id in current_assumptions:
                        continue
                    assumptions.append(assume_id)
            return {
                'assumptions': ';'.join(reversed(assumptions)),
                'current_assumptions': ';'.join(current_assumptions) if isinstance(current_assumptions, list) else None
            }

        lines_data.append({
            'code': '<span class="ETV_GlobalExpander">Global initialization</span>',
            'line': None,
            'offset': curr_offset * ' ',
            'hide_id': 'global_scope'
        })

        for n in trace:
            edge_data = self.data['edges'][n]
            line = str(edge_data.get('start line', None))
            if 'source' in edge_data:
                code = edge_data['source']
            else:
                continue
            if 'file' in edge_data:
                file = self.data['files'][edge_data['file']]
            if file is None:
                line = None

            if line is not None and len(line) > max_line_length:
                max_line_length = len(line)

            line_data = {
                'line': line,
                'file': file,
                'code': code,
                'offset': curr_offset * ' ',
                'class': scope_stack[-1]
            }
            if line_data['line'] is not None and 'assumption' not in edge_data and self.include_assumptions:
                line_data.update(fill_assumptions())
            if 'note' in edge_data:
                line_data['note'] = edge_data['note']
                if all(ss not in scopes_to_hide for ss in scope_stack):
                    for ss in scope_stack[1:]:
                        if ss not in scopes_to_show:
                            scopes_to_show.append(ss)
            if 'warn' in edge_data:
                line_data['warning'] = edge_data['warn']
                for ss in scope_stack[1:]:
                    if ss not in scopes_to_show:
                        scopes_to_show.append(ss)

            if 'assumption' in edge_data:
                if not has_main and 'assumption scope' in edge_data \
                        and self.data['funcs'][edge_data['assumption scope']] == 'entry_point':
                    cnt += 1
                    scope_stack.append('scope__klever_main__%s' % str(cnt))
                    scopes_to_show.append(scope_stack[-1])
                    line_data['class'] = scope_stack[-1]
                    has_main = True
                if 'assumption scope' in edge_data:
                    ass_scope = scope_stack[-1]
                else:
                    ass_scope = 'global'

                if self.include_assumptions:
                    if ass_scope not in assume_scopes:
                        assume_scopes[ass_scope] = []
                    curr_assumes = []
                    for assume in edge_data['assumption'].split(';'):
                        if len(assume) == 0:
                            continue
                        assume_scopes[ass_scope].append(assume)
                        curr_assumes.append('%s_%s' % (ass_scope, str(len(assume_scopes[ass_scope]) - 1)))

                    line_data.update(fill_assumptions(curr_assumes))
            if 'enter' in edge_data:
                if scope_stack[-1] == 'global':
                    cnt += 1
                    scope_stack.append('scope__klever_main__%s' % str(cnt))
                    scopes_to_show.append(scope_stack[-1])
                    line_data['class'] = scope_stack[-1]
                    has_main = True
                cnt += 1
                scope_stack.append('scope__%s__%s' % (self.data['funcs'][edge_data['enter']], str(cnt)))
                line_data['hide_id'] = scope_stack[-1]
                if 'note' in edge_data or 'warn' in edge_data:
                    scopes_to_hide.append(scope_stack[-1])
                line_data['code'] = re.sub(
                    '(^|\W)' + self.data['funcs'][edge_data['enter']] + '(\W|$)',
                    '\g<1><span class="ETV_Fname">' + self.data['funcs'][edge_data['enter']] + '</span>\g<2>',
                    line_data['code']
                )
                lines_data.append(line_data)
                curr_offset += TAB_LENGTH
            elif 'return' in edge_data:
                lines_data.append(line_data)
                if curr_offset >= TAB_LENGTH:
                    curr_offset -= TAB_LENGTH
                add_fake_line('<span class="ETV_DownHideLink"><i class="ui mini icon violet caret up link"></i></span>')
                try:
                    scope_stack.pop()
                    if len(scope_stack) == 0:
                        self.error = 'The error trace is corrupted'
                        return None
                except IndexError:
                    self.error = 'The error trace is corrupted'
                    return None
            elif 'condition' in edge_data:
                m = re.match('^\s*\[(.*)\]\s*$', line_data['code'])
                if m is not None:
                    line_data['code'] = m.group(1)
                line_data['code'] = '<span class="ETV_CondAss">assume(</span>' + \
                                    str(line_data['code']) + '<span class="ETV_CondAss">);</span>'
                lines_data.append(line_data)
            else:
                lines_data.append(line_data)

        while len(scope_stack) > 2:
            if curr_offset >= TAB_LENGTH:
                curr_offset -= TAB_LENGTH
            add_fake_line('<span class="ETV_DownHideLink"><i class="ui mini icon violet caret up link"></i></span>')
            scope_stack.pop()
        for i in range(0, len(lines_data)):
            if lines_data[i]['line'] is None:
                lines_data[i]['line_offset'] = ' ' * max_line_length
            else:
                lines_data[i]['line_offset'] = ' ' * (max_line_length - len(lines_data[i]['line']))
            other_line_offset = '\n  ' + lines_data[i]['offset'] + ' ' * max_line_length
            lines_data[i]['code'] = other_line_offset.join(lines_data[i]['code'].split('\n'))
            lines_data[i]['code'] = self.__parse_code(lines_data[i]['code'])
            if 'class' not in lines_data[i]:
                continue
            a = 'warning' in lines_data[i]
            b = 'note' in lines_data[i]
            c = lines_data[i]['class'] not in scopes_to_show
            d = 'hide_id' not in lines_data[i] or lines_data[i]['hide_id'] is None
            e = 'hide_id' in lines_data[i] and lines_data[i]['hide_id'] is not None \
                and lines_data[i]['hide_id'] not in scopes_to_show
            if a or b and (d or e or c) or not a and not b and c and (d or e):
                lines_data[i]['hidden'] = True
                if e:
                    lines_data[i]['collapsed'] = True
            elif e:
                lines_data[i]['collapsed'] = True
            if a or b:
                lines_data[i]['commented'] = True
                lines_data[i]['note_line_offset'] = ' ' * max_line_length
            if b and c:
                lines_data[i]['note_hidden'] = True
        lines_data.append({'class': 'ETV_End_of_trace'})
        self.html_traces.append(lines_data)

        trace_assumes = []
        for sc in assume_scopes:
            as_cnt = 0
            for a in assume_scopes[sc]:
                trace_assumes.append(['%s_%s' % (sc, as_cnt), a])
                as_cnt += 1
        self.assumes.append(trace_assumes)

    def __wrap_code(self, code, code_type):
        self.ccc = 0
        if code_type in SOURCE_CLASSES:
            return '<span class="%s">%s</span>' % (SOURCE_CLASSES[code_type], code)
        return code

    def __parse_code(self, code):
        m = re.match('(.*?)(<span.*?</span>)(.*)', code)
        if m is not None:
            return "%s%s%s" % (
                self.__parse_code(m.group(1)),
                m.group(2),
                self.__parse_code(m.group(3))
            )
        m = re.match('(.*?)<(.*)', code)
        while m is not None:
            code = m.group(1) + '&lt;' + m.group(2)
            m = re.match('(.*?)<(.*)', code)
        m = re.match('(.*?)>(.*)', code)
        while m is not None:
            code = m.group(1) + '&gt;' + m.group(2)
            m = re.match('(.*?)>(.*)', code)

        m = re.match('(.*?)(/\*.*?\*/)(.*)', code)
        if m is not None:
            return "%s%s%s" % (
                self.__parse_code(m.group(1)),
                self.__wrap_code(m.group(2), 'comment'),
                self.__parse_code(m.group(3))
            )
        m = re.match('(.*?)([\'\"])(.*)', code)
        if m is not None:
            m2 = re.match('(.*?)%s(.*)' % m.group(2), m.group(3))
            if m2 is not None:
                return "%s%s%s" % (
                    self.__parse_code(m.group(1)),
                    self.__wrap_code(m.group(2) + m2.group(1) + m.group(2), 'text'),
                    self.__parse_code(m2.group(2))
                )
        m = re.match('(.*?\W)(\d+)(\W.*)', code)
        if m is not None:
            return "%s%s%s" % (
                self.__parse_code(m.group(1)),
                self.__wrap_code(m.group(2), 'number'),
                self.__parse_code(m.group(3))
            )
        words = re.split('([^a-zA-Z0-9-_#])', code)
        new_words = []
        for word in words:
            if word in KEY1_WORDS:
                new_words.append(self.__wrap_code(word, 'key1'))
            elif word in KEY2_WORDS:
                new_words.append(self.__wrap_code(word, 'key2'))
            else:
                new_words.append(word)
        return ''.join(new_words)


class GetSource(object):
    def __init__(self, report_id, file_name):
        self.error = None
        self.report = self.__get_report(report_id)
        if self.error is not None:
            return
        self.is_comment = False
        self.is_text = False
        self.text_quote = None
        self.data = self.__get_source(file_name)

    def __get_report(self, report_id):
        try:
            return ReportUnsafe.objects.get(pk=int(report_id))
        except ObjectDoesNotExist:
            self.error = _("Could not find the corresponding unsafe")
            return None
        except ValueError:
            self.error = _("Unknown error")
            return None

    def __get_source(self, file_name):
        data = ''
        if file_name.startswith('/'):
            file_name = file_name[1:]
        afc = ArchiveFileContent(self.report.archive, file_name=file_name)
        if afc.error is not None:
            self.error = afc.error
            return None
        cnt = 1
        lines = afc.content.split('\n')
        for line in lines:
            line = line.replace('\t', ' ' * TAB_LENGTH)
            line_num = ' ' * (len(str(len(lines))) - len(str(cnt))) + str(cnt)
            data += '<span>%s %s</span><br>' % (
                self.__wrap_line(line_num, 'line', 'ETVSrcL_%s' % cnt), self.__parse_line(line)
            )
            cnt += 1
        return data

    def parse_line(self, line):
        return self.__parse_line(line)

    def __parse_line(self, line):
        m = re.match('(.*?)<(.*)', line)
        while m is not None:
            line = m.group(1) + '&lt;' + m.group(2)
            m = re.match('(.*?)<(.*)', line)
        m = re.match('(.*?)>(.*)', line)
        while m is not None:
            line = m.group(1) + '&gt;' + m.group(2)
            m = re.match('(.*?)>(.*)', line)

        if self.is_comment:
            m = re.match('(.*?)\*/(.*)', line)
            if m is None:
                return self.__wrap_line(line, 'comment')
            self.is_comment = False
            new_line = self.__wrap_line(m.group(1) + '*/', 'comment')
            return new_line + self.__parse_line(m.group(2))

        if self.is_text:
            before, after = self.__parse_text(line)
            if after is None:
                return self.__wrap_line(before, 'text')
            self.is_text = False
            return self.__wrap_line(before, 'text') + self.__parse_line(after)

        m = re.match('(.*?)/\*(.*)', line)
        if m is not None:
            new_line = self.__parse_line(m.group(1))
            self.is_comment = True
            new_line += self.__parse_line('/*' + m.group(2))
            return new_line
        m = re.match('(.*?)//(.*)', line)
        if m is not None:
            new_line = self.__parse_line(m.group(1))
            new_line += self.__wrap_line('//' + m.group(2), 'comment')
            return new_line
        m = re.match('(.*?)"(.*)', line)
        if m is not None:
            new_line = self.__parse_line(m.group(1))
            self.text_quote = '"'
            before, after = self.__parse_text(m.group(2))
            new_line += self.__wrap_line('"' + before, 'text')
            if after is None:
                self.is_text = True
                return new_line
            self.is_text = False
            return new_line + self.__parse_line(after)
        m = re.match("(.*?)'(.*)", line)
        if m is not None:
            new_line = self.__parse_line(m.group(1))
            self.text_quote = "'"
            before, after = self.__parse_text(m.group(2))
            new_line += self.__wrap_line("'" + before, 'text')
            if after is None:
                self.is_text = True
                return new_line
            self.is_text = False
            return new_line + self.__parse_line(after)
        m = re.match("(.*\W)(\d+)(\W.*)", line)
        if m is not None:
            new_line = self.__parse_line(m.group(1))
            new_line += self.__wrap_line(m.group(2), 'number')
            new_line += self.__parse_line(m.group(3))
            return new_line
        words = re.split('([^a-zA-Z0-9-_#])', line)
        new_words = []
        for word in words:
            if word in KEY1_WORDS:
                new_words.append(self.__wrap_line(word, 'key1'))
            elif word in KEY2_WORDS:
                new_words.append(self.__wrap_line(word, 'key2'))
            else:
                new_words.append(word)
        return ''.join(new_words)

    def __parse_text(self, text):
        escaped = False
        before = ''
        after = ''
        end_found = False
        for c in text:
            if end_found:
                after += c
                continue
            if not escaped and c == self.text_quote:
                end_found = True
            elif escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            before += c
        if end_found:
            return before, after
        return before, None

    def __wrap_line(self, line, text_type, line_id=None):
        self.ccc = 0
        if text_type not in SOURCE_CLASSES:
            return line
        if line_id is not None:
            return '<span id="%s" class="%s">%s</span>' % (line_id, SOURCE_CLASSES[text_type], line)
        return '<span class="%s">%s</span>' % (SOURCE_CLASSES[text_type], line)


def is_tag(tag, name):
    return bool(re.match('^({.*})*' + name + '$', tag))


# Returns json serializable data in case of success or Exception
def error_trace_callstack(error_trace):
    data = json.loads(error_trace)
    call_stacks = []
    for edge_trace in get_error_paths(data):
        call_stack = []
        for edge_id in edge_trace:
            edge_data = data['edges'][edge_id]
            if 'enter' in edge_data:
                call_stack.append(data['funcs'][edge_data['enter']])
            if 'return' in edge_data:
                call_stack.pop()
            if 'warn' in edge_data:
                break
        call_stacks.append(call_stack)
    return call_stacks


# Some constants for internal representation of error traces.
_CALL = 'CALL'
_RET = 'RET'


# Extracts model functions in specific format with some heuristics.
# TODO: error_trace is json already, not graphml
def error_trace_model_functions(error_trace):

    # TODO: Very bad method.
    model_functions = set()
    for line in error_trace.split("\n"):
        res = re.search(r'<data key=\"enterFunction\">ldv_linux_(.*)</data>', line)
        if res:
            mf = res.group(1)
            model_functions.add(mf)

    call_tree = [{"entry_point": _CALL}]
    for line in error_trace.split("\n"):
        res = re.search(r'<data key=\"enterFunction\">(.*)</data>', line)
        if res:
            function_call = res.group(1)
            call_tree.append({function_call: _CALL})

        res = re.search(r'<data key=\"returnFrom\">(.*)</data>', line)
        if res:
            function_return = res.group(1)
            is_done = False
            for mf in model_functions:
                if function_return.__contains__(mf):
                    call_tree.append({function_return: _RET})
                    is_done = True

            if not is_done:
                # Check from the last call of that function.
                is_save = False
                sublist = []
                for elem in reversed(call_tree):
                    sublist.append(elem)
                    func_name = list(elem.keys()).__getitem__(0)
                    for mf in model_functions:
                        if func_name.__contains__(mf):
                            is_save = True
                    if elem == {function_return: _CALL}:
                        sublist.reverse()
                        break
                if is_save:
                    call_tree.append({function_return: _RET})
                else:
                    call_tree = call_tree[:-sublist.__len__()]

    # Maybe for debug print?
    level = 0
    for elem in call_tree:
        func_name, op = list(elem.items())[0]
        spaces = ""
        for i in range(0, level):
            spaces += " "
        if op == _CALL:
            level += 1
            print(spaces + func_name)
        else:
            level -= 1

    return json.dumps(call_tree, ensure_ascii=False, sort_keys=True, indent=4)


class ErrorTraceCallstackTree(object):
    def __init__(self, error_trace):
        self.data = json.loads(error_trace)
        self.trace = []
        for edge_trace in get_error_paths(self.data):
            self.trace.append(self.__get_tree(edge_trace))

    def __get_tree(self, edge_trace):
        tree = []
        call_level = 0
        call_stack = []
        model_functions = []
        for edge_id in edge_trace:
            edge_data = self.data['edges'][edge_id]
            if 'enter' in edge_data:
                call_stack.append(self.data['funcs'][edge_data['enter']])
                call_level += 1
                while len(tree) <= call_level:
                    tree.append([])
                if 'note' in edge_data:
                    model_functions.append(self.data['funcs'][edge_data['enter']])
                tree[call_level].append({
                    'name': self.data['funcs'][edge_data['enter']],
                    'parent': call_stack[-2] if len(call_stack) > 1 else None
                })
            if 'return' in edge_data:
                call_stack.pop()
                call_level -= 1

        def not_model_leaf(ii, jj):
            if tree[ii][jj]['name'] in model_functions:
                return False
            elif len(tree) > ii + 1:
                for ch_j in range(0, len(tree[ii + 1])):
                    if tree[ii + 1][ch_j]['parent'] == tree[ii][jj]['name']:
                        return False
            return True

        for i in reversed(range(0, len(tree))):
            new_level = []
            for j in range(0, len(tree[i])):
                if not not_model_leaf(i, j):
                    new_level.append(tree[i][j])
            if len(new_level) == 0:
                del tree[i]
            else:
                tree[i] = new_level
        just_names = []
        for level in tree:
            new_level = []
            for f_data in level:
                new_level.append(f_data['name'])
            just_names.append(' '.join(sorted(str(x) for x in new_level)))
        return just_names
