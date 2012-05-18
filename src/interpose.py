#!/usr/bin/python

import subprocess
from textwrap import dedent

# platform.system() == 'Darwin'

class Interpose(object):
   def __init__(self, header, lib, api):
      self.header = header
      self.lib = lib
      #self.out_lib = 'libinterpose_{0}.so'.format(self.header)
      self.out_lib = 'libinterpose_{0}.dylib'.format(self.header)
      self.out_body = 'interpose_{0}.c'.format(self.header)
      self.api = api
      self.code = ''
      self.wrote = False
   def generate(self):
      if not self.code:
         includes=(
            '<stdio.h>',
            '<dlfcn.h>',
            '<sys/time.h>',
            '"{0}"'.format(self.header))
         result = '\n'.join('#include {0}'.format(i) for i in includes) + dedent('''

         struct timeval current_time()
         {
            // store a precise time-stamp
            struct timeval time;

            // capture the current time
            gettimeofday(&time, NULL);
            
            // return the time
            return time;
         }
         ''')
         for function in self.api:
            name, args, retn = function[:3]
            if retn == 'void':
               save_result = ''
               retn_result = ''
               dflt_result = 'return;'
            else:
               dflt = function[3]
               save_result = "{0} result = ".format(retn)
               retn_result = '''
               
               // return the actual result
               return result;'''
               dflt_result = "return {0};".format(dflt)
            result += dedent((
            '''
            {0} {1}({2})
            {{
               // points to the original function being interposed
               static {0} (*real_{1})({3}) = NULL;

               // record the timestamp before the call
               struct timeval call_timestamp = current_time();

               // print the time-stamp
               printf
               (
                  "[%011llu.%06llu][call] {1}()\\n",
                  (long long unsigned)call_timestamp.tv_sec,
                  (long long unsigned)call_timestamp.tv_usec
               );

               // find the original function
               if(!real_{1})
               {{
                  // grab handle to the original library
                  void *handle = dlopen("{8}", RTLD_NOW);

                  // find the original function within that library
                  real_{1} = ({0} (*)({3}))dlsym(handle, "{1}");

                  // if the original function is not found...
                  if(!real_{1})
                  {{
                     // ...print an error...
                     printf("   >>> ERROR: {1}() not found\\n");

                     // ...and return immediately
                     {7}
                  }}
               }}

               // run the original function
               {5}real_{1}({4});

               // record the timestamp after the call
               struct timeval done_timestamp = current_time();

               // print the time-stamp
               printf
               (
                  "   >>> duration: %llu.%06llu seconds\\n"
                  "[%011llu.%06llu][done] {1}()\\n",
                  (long long unsigned)(done_timestamp.tv_sec  - call_timestamp.tv_sec),
                  (long long unsigned)(done_timestamp.tv_usec - call_timestamp.tv_usec),
                  (long long unsigned)done_timestamp.tv_sec,
                  (long long unsigned)done_timestamp.tv_usec
               );{6}
            }}
            ''').format(
               retn,
               name,
               ', '.join('{0} {1}'.format(arg[1], arg[0]) for arg in args),
               ', '.join(arg[1] for arg in args),
               ', '.join(arg[0] for arg in args),
               save_result,
               retn_result,
               dflt_result,
               self.lib))
         self.code = result
      return self.code
   def write(self):
      if not self.wrote:
         with open(self.out_body, 'w') as f:
            f.write(self.generate())
         self.wrote = True
   def build(self):
      self.write()
      #subprocess.call(['gcc', '-shared', '-fPIC', '-Wall', '-Werror', '-std=c99', '-D_GNU_SOURCE', '-o', self.out_lib, self.out_header, '-ldl'])
      subprocess.call(['gcc', '-flat_namespace', '-dynamiclib', '-fPIC', '-Wall', '-Werror', '-std=c99', '-o', self.out_lib, self.out_body])

def main():
   API=('test_api.h', 'libtest_api.dylib', ('api_call', (('argc','int'),('argv', 'char **')), 'int', '-1'), ('api_simple', (), 'void'))
   i = Interpose(header = API[0], lib = API[1], api = API[2:])
   i.build()

if __name__ == "__main__":
   main()
