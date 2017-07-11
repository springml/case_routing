# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Resource filters supplementary help."""

import textwrap

from googlecloudsdk.calliope import base
from googlecloudsdk.core.resource import resource_topics


class Filters(base.TopicCommand):
  """Resource filters supplementary help."""

  detailed_help = {

      'DESCRIPTION': textwrap.dedent("""\
          {description}

          === Filter Expressions ===

          A filter expression is a Boolean function that selects the resources
          to print from a list of resources. Expressions are composed
          of terms connected by logic operators.

          *LogicOperator*::

          Expressions containing both *AND* and *OR* must be parenthesized to
          disambiguate precedence.

          *NOT* _term-1_:::

          True if _term-1_ is False, otherwise False.

          _term-1_ *AND* _term-2_:::

          True if both _term-1_ and _term-2_ are true.

          _term-1_ *OR* _term-2_:::

          True if at least one of _term-1_ or _term-2_ is true.

          _term-1_ _term-2_:::

          True if both _term-1_ and _term-2_ are true. Implicit conjunction has
          lower precedence than *OR*.

          *Terms*::

          A term is a _key_ _operator_ _value_ tuple, where _key_ is a dotted
          name that evaluates to the value of a resource attribute, and _value_
          may be:

          *number*::: integer or floating point numeric constant

          *unquoted literal*::: character sequence terminated by space, ( or )

          *quoted literal*::: _"..."_ or _'...'_

          Most filter expressions need to be quoted in shell commands. If you
          use _'...'_ shell quotes then use _"..."_ filter string literal quotes
          and vice versa.

          *Operator Terms*::

          _key_ *=* _value_:::

          True if _key_ is equal to _value_.

          _key_ *=(* _value_ ... *)*:::

          True if _key_ is equal to any _value_ in the
          (space, tab, newline, *,*) separated list.

          _key_ *!=* _value_:::

          True if _key_ is not _value_. Equivalent to
          -_key_=_value_ and NOT _key_=_value_.

          _key_ *<* _value_:::

          True if _key_ is less than _value_. If both _key_ and
          _value_ are numeric then numeric comparison is used, otherwise
          lexicographic string comparison is used.

          _key_ *<=* _value_:::

          True if _key_ is less than or equal to _value_. If both
          _key_ and _value_ are numeric then numeric comparison is used,
          otherwise lexicographic string comparison is used.

          _key_ *>=* _value_:::

          True if _key_ is greater than or equal to _value_. If
          both _key_ and _value_ are numeric then numeric comparison is used,
          otherwise lexicographic string comparison is used.

          _key_ *>* _value_:::

          True if _key_ is greater than _value_. If both _key_ and
          _value_ are numeric then numeric comparison is used, otherwise
          lexicographic string comparison is used.

          _key_ *:* _simple-pattern_:::

          True if _key_ matches _simple-pattern_. The match is anchored (all
          characters must match), case insensitive, and allows one ```*```
          operator that matches any sequence of 0 or more characters. The
          pattern ```abc``` matches ```abc```, the pattern ```abc*``` matches
          ```abc``` and ```abcxyz```, the pattern ```*xyz``` matches ```xyz```
          and ```abcxyz```, and the pattern ```*``` matches any non-empty
          string. Use _key_```:*``` to test if _key_ is defined and
          ```-```_key_```:*``` to test if _key_ is undefined.

          _key_ *:(* _simple-pattern_ ... *)*:::

          True if _key_ matches any _simple-pattern_ in the
          (space, tab, newline, comma) separated list.

          _key_ *~* _value_:::

          True if _key_ matches the RE (regular expression) pattern _value_.

          _key_ *!*~ _value_:::

          True if _key_ does not match the RE (regular expression)
          pattern _value_.

          """).format(
              description=resource_topics.ResourceDescription('filter')),

      'EXAMPLES': textwrap.dedent("""\
          List all instances resources:

            $ gcloud compute instances list

          List instances resources that have machineType *f1-micro*:

            $ gcloud compute instances list --filter='machineType:f1-micro'

          List resources with zone prefix *us* and not MachineType *f1-micro*:

            $ gcloud compute instances list --filter='zone ~ ^us AND -machineType:f1-micro'

          List in JSON format those projects where the labels match specific
          values (e.g. label.env is 'test' and label.version is alpha):

            $ gcloud projects list --format="json" --filter="labels.env=test AND labels.version=alpha"

          List projects that were created after a specific date:

            $ gcloud projects list --format="table(projectNumber,projectId,createTime)" --filter="createTime.date('%Y-%m-%d', Z)='2016-05-11'"

          Note that in the last example, a projection on the key was used. The
          filter is applied on the createTime key after the date formatting is
          set.
          """),
      }
